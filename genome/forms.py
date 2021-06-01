import re
from io import StringIO
from typing import Optional

from django import forms as forms
from django.db import transaction
from django.forms.models import BaseModelFormSet
from django.forms import modelformset_factory
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe

from fqfa.fasta.fasta import parse_fasta_records

from core.utilities import is_null
from dataset.models import ScoreSet

from .validators import (
    validate_interval_start_lteq_end,
    validate_wildtype_sequence,
    validate_gene_name,
)

from .models import (
    TargetGene,
    ReferenceMap,
    ReferenceGenome,
    GenomicInterval,
    WildTypeSequence,
)


# TargetGene
# ------------------------------------------------------------------------ #
class TargetGeneForm(forms.ModelForm):
    """
    Form for validating the fields required to instantiate the following:

        - :class:`WildTypeSequence`
        - :class:`TargetGene`

    The wildtype sequence will be created from `wt_sequence` and then
    associated with the :class:`TargetGene` instance that will be created
    upon saving.
    """

    class Meta:
        model = TargetGene
        fields = ("name", "category")

    sequence_text = forms.CharField(
        label="Target reference sequence",
        required=False,
        widget=forms.Textarea(),
        error_messages={
            "required": "You must supply a reference sequence for your target."
        },
    )
    sequence_fasta = forms.FileField(
        label="FASTA file",
        required=False,
    )
    sequence_type = forms.CharField(
        label="Sequence type",
        required=True,
        help_text=mark_safe(
            "Select <b>DNA</b> for a nucleotide sequence, "
            "<b>Protein</b> for an amino acid sequence, "
            "or <b>Infer</b> to automatically infer a sequence type."
        ),
        widget=forms.Select(choices=WildTypeSequence.SequenceType.choices()),
        initial=WildTypeSequence.SequenceType.INFER,
    )
    target = forms.ModelChoiceField(
        label="Existing target",
        required=False,
        queryset=None,
        widget=forms.Select(attrs={"class": "select2"}),
    )

    def __init__(self, *args, **kwargs):
        self.field_order = (
            "target",
            "name",
            "category",
            "sequence_type",
            "sequence_fasta",
            "sequence_text",
        )
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        instance = kwargs.get("instance", None)
        self.sequence_params = dict(sequence=None, sequence_type=None)
        self.sequence_is_protein = False

        if instance and instance.get_wt_sequence():
            sequence = instance.get_wt_sequence().sequence
            sequence_type = instance.get_wt_sequence().sequence_type

            self.sequence_is_protein = (
                WildTypeSequence.SequenceType.is_protein(sequence_type)
            )
            self.sequence_params.update(
                sequence=sequence,
                sequence_type=sequence_type,
            )
            self.fields["sequence_text"].initial = sequence
            self.fields["sequence_type"].initial = sequence_type

        self.set_target_gene_options()

        self.fields["category"].choices = [
            ("", self.fields["target"].empty_label)
        ] + list(self.fields["category"].choices)
        self.fields["category"].initial = ""

        self.fields["name"].label = "Target name"
        self.fields["name"].validators = [validate_gene_name]
        self.fields["name"].widget = forms.TextInput()
        self.fields["name"].error_messages.update(
            {"required": "You must supply a name for your target."}
        )

    def set_target_gene_options(self):
        if "target" in self.fields:
            choices = set()
            targets = TargetGene.objects.all()
            user_scoresets = self.user.profile.contributor_scoresets()
            for target in targets:
                scoreset = target.scoreset
                if scoreset.private and scoreset in user_scoresets:
                    choices.add(target.pk)
                elif not scoreset.private:
                    choices.add(target.pk)

            targets_qs = (
                TargetGene.objects.filter(pk__in=choices)
                .order_by("scoreset__urn")
                .order_by("name")
            )
            self.fields["target"].initial = ""
            self.fields["target"].queryset = targets_qs
            self.fields["target"].choices = [
                ("", self.fields["target"].empty_label)
            ] + [
                (t.pk, "{} | {}".format(t.get_unique_name(), t.scoreset.title))
                for t in targets_qs.all()
            ]

    # ----------------------- Cleaning ------------------------------------ #
    def clean_sequence_fasta(self):
        fasta = self.files.get("sequence_fasta", None)
        sequence_type = self.cleaned_data.get("sequence_type")

        content = fasta.read() if fasta else ""
        if hasattr(content, "decode"):
            content = content.decode("utf-8")

        sequence = None
        for _, seq in parse_fasta_records(StringIO(content)):
            validate_wildtype_sequence(seq, as_type=sequence_type)
            sequence = seq
            break  # Only take first

        return sequence

    def clean_sequence_text(self):
        sequence = self.cleaned_data.get("sequence_text", None)
        sequence_type = self.cleaned_data.get("sequence_type")

        if isinstance(sequence, str):
            sequence = sequence.strip()

        if sequence:
            # Ignore FASTA header
            sequence = "\n".join(
                [
                    line
                    for line in sequence.split("\n")
                    if not line.strip().startswith(">")
                ]
            )
            sequence = re.sub(r"\\r|\\n|\\t|\s+", "", sequence)
            validate_wildtype_sequence(sequence, as_type=sequence_type)

        return sequence

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        sequence_text = cleaned_data.get("sequence_text")
        sequence_fasta = cleaned_data.get("sequence_fasta")
        sequence_type = cleaned_data.get("sequence_type")
        sequence = sequence_text or sequence_fasta

        if sequence_text and sequence_fasta:
            self.add_error(
                None,
                (
                    "Please supply either a FASTA sequence or a sequence via "
                    "the text box, but not both."
                ),
            )
            return cleaned_data

        if not (sequence_text or sequence_fasta):
            self.add_error(
                None,
                (
                    "A reference sequence is required. Please supply either "
                    "a FASTA sequence or a sequence via the text box."
                ),
            )
            return cleaned_data

        self.sequence_is_protein = WildTypeSequence.SequenceType.is_protein(
            WildTypeSequence.SequenceType.detect_sequence_type(sequence)
        )
        self.sequence_params.update(
            sequence=sequence,
            sequence_type=sequence_type,
        )

        return cleaned_data

    # -------------------------- Post clean -------------------------------- #
    @transaction.atomic
    def save(self, commit: bool = True, scoreset: Optional[ScoreSet] = None):
        if not self.is_valid():
            raise ValidationError(
                "Some target gene fields are invalid. Please address the "
                "errors and re-submit."
            )

        existing_seq = self.instance.get_wt_sequence()
        if existing_seq is not None:
            existing_seq.sequence_type = self.sequence_params["sequence_type"]
            existing_seq.sequence = self.sequence_params["sequence"]
        else:
            existing_seq = WildTypeSequence(**self.sequence_params)

        if scoreset is not None:
            self.instance.scoreset = scoreset

        if commit:
            existing_seq.save()
            self.instance.set_wt_sequence(existing_seq)

        return super().save(commit=commit)

    def get_targetseq(self) -> Optional[str]:
        if self.errors:
            return None
        return self.sequence_params.get("sequence").upper()

    def get_targetseq_type(self) -> Optional[str]:
        if self.errors:
            return None
        return self.sequence_params.get("sequence_type")


# GenomicInterval
# ------------------------------------------------------------------------ #
class GenomicIntervalForm(forms.ModelForm):
    """
    Form for validating interval input and instantiating a valid instance.
    """

    class Meta:
        model = GenomicInterval
        fields = ("start", "end", "chromosome", "strand")

    def __init__(self, *args, **kwargs):
        self.field_order = ("start", "end", "chromosome", "strand")
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True

    def clean_start(self):
        start = self.cleaned_data.get("start", None)
        if is_null(start):
            raise ValidationError("A valid start coordinate is required.")
        return start

    def clean_end(self):
        end = self.cleaned_data.get("end", None)
        if is_null(end):
            raise ValidationError("An valid end coordinate is required.")
        return end

    def clean_chromosome(self):
        value = self.cleaned_data.get("chromosome", None)
        if is_null(value):
            raise ValidationError("A valid chromosome is required.")
        return value

    def clean_strand(self):
        value = self.cleaned_data.get("strand", None)
        if is_null(value):
            raise ValidationError("A valid strand is required.")
        return value

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data
        else:
            start = cleaned_data.get("start", None)
            end = cleaned_data.get("end", None)
            validate_interval_start_lteq_end(start, end)
            return cleaned_data

    def form_is_blank(self):
        start = self.cleaned_data.get("start")
        end = self.cleaned_data.get("end")
        chr_ = self.cleaned_data.get("chromosome")
        strand = self.cleaned_data.get("strand")
        return all([is_null(elem) for elem in [start, end, chr_, strand]])


class BaseGenomicIntervalFormSet(BaseModelFormSet):
    """
    Formset which will validate multiple intervals against each other
    to ensure uniqueness.
    """

    model = GenomicInterval
    form_prefix = "genomic_interval_form"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "queryset" in kwargs:
            self.queryset = kwargs["queryset"]
        else:
            self.queryset = GenomicInterval.objects.none()

    def has_errors(self):
        for form in self.forms:
            # These are not triggering for empty forms. Do them manually.
            form.full_clean()
            form.clean_start()
            form.clean_end()
            form.clean_chromosome()
            form.clean_strand()
        if self.non_form_errors():
            return True
        elif isinstance(self.errors, list):
            return any(self.errors)
        else:
            return bool(self.errors)

    def clean(self):
        if self.has_errors():
            return

        field_values = set()
        for form in self.forms:
            start = form.cleaned_data["start"]
            end = form.cleaned_data["end"]
            chromosome = form.cleaned_data["chromosome"]
            strand = form.cleaned_data["strand"]
            value = (start, end, str(chromosome).lower(), str(strand).lower())
            if value in field_values:
                raise ValidationError(
                    "You can not specify the same interval twice."
                )
            else:
                field_values.add(value)

    def save(self, reference_map=None, commit=True):
        if self.has_errors():
            return super().save(commit)
        if reference_map is not None:
            if reference_map.pk is None:
                raise ValueError(
                    "ReferenceMap must be saved before it can "
                    "be assigned as a related object."
                )
            for form in self.forms:
                form.instance.reference_map = reference_map

        for form in self.forms:
            if form.instance.pk is None and reference_map is None:
                raise ValueError(
                    "Cannot save a GenomicInterval without a "
                    "ReferenceMap instance."
                )

        return super().save(commit)


def create_genomic_interval_formset(extra=2, min_num=1, can_delete=False):
    return modelformset_factory(
        model=GenomicInterval,
        form=GenomicIntervalForm,
        formset=BaseGenomicIntervalFormSet,
        extra=extra,
        min_num=min_num,
        validate_min=True,
        can_delete=can_delete,
        fields=GenomicIntervalForm.Meta.fields,
    )


# ReferenceMap
# ------------------------------------------------------------------------ #
class ReferenceMapForm(forms.ModelForm):
    """
    The reference_map form

    Parameters
    ----------
    annotations : `tuple`
        A tuple of annotations to validate the instance this form will create
        against. Useful for validating all annotations specify unique
        references.

    intervals : `tuple`
        A tuple of valid intervals to associate with the reference_map.
    """

    class Meta:
        model = ReferenceMap
        fields = ("is_primary", "genome")

    def __init__(self, *args, **kwargs):
        self.field_order = ("is_primary", "genome")
        super().__init__(*args, **kwargs)
        genomes = self._display_ordered_genomes()
        genome_field = self.fields["genome"]
        genome_field.requried = True
        genome_field.queryset = genomes
        genome_field.choices = [("", genome_field.empty_label)] + [
            (r.pk, r.display_name()) for r in genomes
        ]
        genome_field.initial = ""
        for field in ("genome",):
            if field in self.fields:
                self.fields[field].widget.attrs.update(**{"class": "select2"})

    @staticmethod
    def _display_ordered_genomes():
        genomes = ReferenceGenome.objects.all()
        ordering = {"sacCer3/R64": 1, "Synthetic": 2, "Other": 3}
        ids = [
            g.id
            for g in sorted(
                genomes, key=lambda x: ordering.get(x.short_name, 0)
            )
        ]
        return ReferenceGenome.filter_in_order(
            ids, field="id", expression="in"
        )

    def dummy_instance(self):
        if not self.is_bound or self.errors:
            return None
        return ReferenceMap(
            genome=self.cleaned_data.get("genome"),
            is_primary=self.cleaned_data.get("is_primary"),
        )

    def clean_genome(self):
        genome = self.cleaned_data.get("genome", None)
        if not genome:
            raise ValidationError("You must select a valid reference genome.")
        return genome


class PrimaryReferenceMapForm(ReferenceMapForm):
    """
    Same as `ReferenceMapForm` except `is_primary` is popped and always
    sets as True.
    """

    def __init__(self, *args, **kwargs):
        super(PrimaryReferenceMapForm, self).__init__(*args, **kwargs)
        self.fields.pop("is_primary")

    def clean_is_primary(self):
        return True
