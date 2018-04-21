from django import forms as forms
from django.db import transaction
from django.forms.models import BaseModelFormSet
from django.core.exceptions import ValidationError

from .validators import (
    validate_interval_start_lteq_end,
    validate_wildtype_sequence,
    validate_gene_name,
    validate_at_least_one_map,
    validate_unique_intervals,
    validate_map_has_unique_reference_genome,
    validate_one_primary_map
)

from .models import (
    TargetGene,
    ReferenceMap,
    ReferenceGenome,
    GenomicInterval,
    WildTypeSequence,
)

BOOTSTRAP_CLASS = 'form-control'


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
        fields = ('name', )

    wt_sequence = forms.CharField(
        label='Target wild-type sequence',
        required=True,
        widget=forms.Textarea(attrs={'class': BOOTSTRAP_CLASS}),
        validators=[validate_wildtype_sequence],
        error_messages={
            'required':
                'You must supply a wild-type sequence for your target.'
        },
    )
    target = forms.ModelChoiceField(
        label='Existing target', required=False,
        help_text='Autofill the fields below using an existing target.',
        queryset=None,
        widget=forms.Select(
            attrs={"class": "form-control"})
    )

    def __init__(self, *args, **kwargs):
        self.field_order = ('target', 'name', 'wt_sequence')
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

        instance = kwargs.get('instance', None)
        self.wt_sequence = None
        if instance and instance.get_wt_sequence():
            self.fields['wt_sequence'].initial = \
                instance.get_wt_sequence().get_sequence()

        self.set_target_gene_options()

        self.fields['name'].label = 'Target name'
        self.fields['name'].validators = [validate_gene_name]
        self.fields['name'].widget = forms.TextInput(
            attrs={'class': BOOTSTRAP_CLASS})
        self.fields['name'].error_messages.update(
            {'required': 'You must supply a name for your target.'})

    def clean_wt_sequence(self):
        sequence = self.cleaned_data.get('wt_sequence', None)
        if sequence is None:
            raise ValidationError("Sequence cannot be empty.")
        self.wt_sequence = sequence
        return sequence

    def set_target_gene_options(self):
        if 'target' in self.fields:
            choices = set()
            targets = TargetGene.objects.all()
            user_scoresets = self.user.profile.contributor_scoresets()
            for target in targets:
                scoreset = target.scoreset
                if scoreset.private and scoreset in user_scoresets:
                    choices.add(target.pk)
                elif not scoreset.private:
                    choices.add(target.pk)

            targets_qs = TargetGene.objects.filter(
                pk__in=choices).order_by("name")
            self.fields["target"].queryset = targets_qs
            self.fields["target"].choices = \
                [("", self.fields["target"].empty_label)] + [
                (t.pk, t.get_unique_name()) for t in targets_qs.all()
            ]
            self.fields["target"].initial = ""

    @transaction.atomic
    def save(self, commit=True):
        if not self.is_valid():
            raise ValidationError("Cannot save with invalid data.")

        if self.instance.get_wt_sequence() is not None:
            if isinstance(self.wt_sequence, str):
                self.instance.get_wt_sequence().sequence = self.wt_sequence

        if commit:
            if self.instance.get_wt_sequence() is None:
                self.instance.set_wt_sequence(
                    WildTypeSequence.objects.create(sequence=self.wt_sequence)
                )
            self.instance.get_wt_sequence().save()
            return super().save(commit=True)

        return super().save(commit=False)

    def clean(self):
        cleaned_data = super().clean()
        if not self.errors:
            wt_sequence = cleaned_data.get('wt_sequence', None)
            if not wt_sequence:
                raise ValidationError("You must supply a wild-type sequence.")
            self.wt_sequence = wt_sequence
        return cleaned_data


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
        fields = ('is_primary', 'genome',)

    def __init__(self, *args, **kwargs):
        self.field_order = ('is_primary', 'genome',)
        super().__init__(*args, **kwargs)

        genome_field = self.fields['genome']
        genome_field.widget.attrs.update({"class": BOOTSTRAP_CLASS})
        genome_field.requried = True
        genome_field.queryset = ReferenceGenome.objects.all()
        genome_field.choices = \
            [("", genome_field.empty_label)] + [
                (r.pk, r.display_name()) for r in ReferenceGenome.objects.all()
            ]
        genome_field.initial = ""

        is_primary_field = self.fields['is_primary']
        is_primary_field.widget.attrs.update({"class": BOOTSTRAP_CLASS})

    def dummy_instance(self):
        if self.errors:
            return None
        return ReferenceMap(
            genome=self.cleaned_data.get('genome'),
            is_primary=self.cleaned_data.get('is_primary'),
        )

    def clean_is_primary(self):
        # TODO: Remove this once formsets are working
        return True

    def clean_genome(self):
        genome = self.cleaned_data.get('genome', None)
        if not genome:
            raise ValidationError("You must select a valid reference genome.")
        return genome


class BaseAnnotationFormSet(BaseModelFormSet):
    """
    Formset for handling the validation of :class:`ReferenceMap` instances
    against each other.
    """
    model = ReferenceMap

    def has_errors(self):
        if isinstance(self.errors, list):
            return any(len(dict_) for dict_ in self.errors)
        else:
            return bool(self.errors)

    def clean(self):
        if not self.has_errors():
            maps = [form.dummy_instance() for form in self.forms]
            validate_at_least_one_map(maps)
            validate_map_has_unique_reference_genome(maps)
            validate_one_primary_map(maps)



# GenomicInterval
# ------------------------------------------------------------------------ #
class GenomicIntervalForm(forms.ModelForm):
    """
    Form for validating interval input and instantiating a valid instance.
    """
    class Meta:
        model = GenomicInterval
        fields = ('start', 'end', 'chromosome', 'strand')

    def __init__(self, *args, **kwargs):
        self.field_order = ('start', 'end', 'chromosome', 'strand')
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.required = False
            field.widget.attrs.update({'class': BOOTSTRAP_CLASS})

    def dummy_instance(self):
        if self.errors:
            return None
        return GenomicInterval(
            start=self.cleaned_data.get('start'),
            end=self.cleaned_data.get('end'),
            chromosome=self.cleaned_data.get('chromosome'),
            strand=self.cleaned_data.get('strand'),
        )

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data
        else:
            start = cleaned_data.get('start', None)
            end = cleaned_data.get('end', None)
            chromosome = cleaned_data.get('chromosome', None)
            strand = cleaned_data.get('strand', None)
            if any([v is None for v in [start, end, chromosome, strand]]):
                raise ValidationError(
                    "You must specify all or no fields of an interval."
                )
            validate_interval_start_lteq_end(start, end)
            return cleaned_data


class BaseGenomicIntervalFormSet(BaseModelFormSet):
    """
    Formset which will validate multiple intervals against each other
    to ensure uniqueness.
    """
    model = GenomicInterval

    def has_errors(self):
        if isinstance(self.errors, list):
            return any(len(dict_) for dict_ in self.errors)
        else:
            return bool(self.errors)

    def clean(self):
        if not self.has_errors():
            intervals = [form.dummy_instance() for form in self.forms]
            if not intervals:
                raise ValidationError(
                    "You must specify at least one interval for each "
                    "reference reference_map."
                )
            validate_unique_intervals(intervals)
