import io
import json
from enum import Enum
from typing import Optional

import pandas as pd
from django import forms as forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext

from core.mixins import NestedEnumMixin
from core.utilities import humanized_null_values
from dataset import constants as constants
from main.models import Licence
from variant.validators import MaveDataset
from ..forms.base import DatasetModelForm
from ..models import ExperimentSet
from ..models.experiment import Experiment
from ..models.scoreset import ScoreSet
from ..validators import (
    validate_scoreset_score_data_input,
    validate_csv_extension,
    validate_json_extension,
    validate_scoreset_count_data_input,
    validate_scoreset_json,
)


class ErrorMessages(NestedEnumMixin, Enum):
    """ScoreSet field specific error messages."""

    class Field(Enum):
        invalid_choice = ugettext(
            forms.ModelChoiceField.default_error_messages["invalid_choice"]
        )

    class Experiment(Enum):
        public_scoreset = ugettext(
            "Changing the parent experiment of a public score set is not "
            "supported."
        )
        changing_experiment = ugettext(
            "The parent experiment cannot be changed."
        )

    class MetaAnalysis(Enum):
        experiment_present = ugettext(
            "When submitting a meta-analysis, please leave the experiment "
            "field blank.",
        )
        too_few = ugettext(
            "Please select more than {0} score set(s) to include in this "
            "meta-analysis."
        )
        linking_other_meta = ugettext(
            "A meta-analysis cannot include other meta-analyses score sets."
        )
        linking_private = ugettext(
            "Please select public score sets to use in this meta-analysis."
        )
        changing_children = ugettext(
            "Child score sets of a meta-analysis cannot be changed after "
            "creation. Please delete this score set and create a new one."
        )

    class Replaces(Enum):
        changing_replaces = ugettext(
            "Replaced score set cannot be changed after creation."
        )
        different_experiment = ugettext(
            "A score set can only replace other score sets with the "
            "same experiment."
        )
        already_replaced = ugettext("{} has already been replaced.")
        is_not_public = ugettext("Only public entries can be replaced.")
        replacing_self = ugettext("A score set cannot replace itself.")
        meta_replacing_non_meta = ugettext(
            "A meta-analysis can only replace other meta-analysis score sets."
        )
        non_meta_replacing_meta = ugettext(
            "A non meta-analysis score set can only replace other "
            "non meta-analyses"
        )

    class MetaData(Enum):
        incorrect_format = ugettext("Incorrectly formatted json file: {}")

    class ScoreData(Enum):
        score_file_required = ugettext(
            "You must upload a non-empty scores data file."
        )
        no_variants = ugettext(
            "No variants could be parsed from your input file. "
            "Please upload a non-empty file."
        )

    class CountData(Enum):
        no_score_file = ugettext(
            "You must upload an accompanying score data file when "
            "uploading a new count data file or replacing an "
            "existing one."
        )
        no_variants = ugettext(
            "No variants could be parsed from your input file. "
            "Please upload a non-empty file."
        )
        primary_mismatch = ugettext(
            "The primary hgvs column inferred from the scores file ('{}') does"
            "not match that inferred from the counts file ('{}'). This can "
            "if the two files do not define the same variants across rows."
        )
        different_variants = ugettext(
            "Scores and counts files must define the same variants. Check that "
            "the hgvs columns in both files match and are presented in the "
            "same order."
        )


class ScoreSetForm(DatasetModelForm):
    """
    This form is presented on the create new scoreset view. It contains
    all the validation logic required to ensure that a score dataset and
    counts dataset are parsed into valid Variant objects that are associated
    with the created scoreset. It also defines additional validation for
    the `replaces` field in scoreset to make sure that the selected
    `ScoreSet` is a member of the selected `Experiment` instance.
    """

    MAX_ERRORS = 20

    class Meta(DatasetModelForm.Meta):
        model = ScoreSet
        fields = DatasetModelForm.Meta.fields + (
            "experiment",
            "meta_analysis_for",
            "licence",
            "data_usage_policy",
            "replaces",
        )

    score_data = forms.FileField(
        required=False,
        label="Variant score data",
        help_text=mark_safe(
            f"A valid CSV file containing variant score information. The file "
            f"must at least specify the columns <b>hgvs_nt</b> or "
            f"<b>hgvs_pro</b> (or both) and <b>score</b>. There are no "
            f"constraints on other column names. Apart from the hgvs columns, "
            f"all data must be numeric. You may additionally specify a "
            f"<b>hgvs_tx</b> column containing transcript variants with a "
            f"<b>n.</b> or <b>c.</b> prefix. If a <b>hgvs_tx</b> "
            f"column is present, the <b>hgvs_nt</b> column must only contain "
            f"genomic variants with a <b>g.</b> prefix. Conversely, if your "
            f"<b>hgvs_nt</b> column only specifies genomic variants, a "
            f"<b>hgvs_tx</b> column must also be supplied as described above."
            f"<br><br>"
            f"Row scores that are empty, whitespace or the strings "
            f"{humanized_null_values} (case-insensitive) will be converted to "
            f"a null score. The columns <b>hgvs_nt</b>, <b>hgvs_tx</b> and "
            f"<b>hgvs_pro</b> must define the same variants as those in the "
            f"count file below."
        ),
        validators=[
            validate_scoreset_score_data_input,
            validate_csv_extension,
        ],
        widget=forms.widgets.ClearableFileInput(attrs={"accept": "csv"}),
    )
    count_data = forms.FileField(
        required=False,
        label="Variant count data",
        help_text=mark_safe(
            f"A valid CSV file containing variant count information. The "
            f"hgvs columns in this file must adhere to the same requirements "
            f"as the scores file. Non-hgvs columns must contain numeric count "
            f"data, and there are no name requirements for these columns. "
            f"<br><br>"
            f"Row counts that are empty, whitespace or any of the strings "
            f"{humanized_null_values} (case-insensitive) will be converted to "
            f"a null score. The columns <b>hgvs_nt</b>, <b>hgvs_tx</b> and "
            f"<b>hgvs_pro</b> must define the same variants as those in the "
            f"score file above."
        ),
        validators=[
            validate_scoreset_count_data_input,
            validate_csv_extension,
        ],
        widget=forms.widgets.FileInput(attrs={"accept": "csv"}),
    )

    meta_data = forms.FileField(
        required=False,
        label="Metadata",
        help_text=(
            "You can upload a JSON file containing additional information "
            "not available as a field in this form."
        ),
        validators=[validate_json_extension],
        widget=forms.widgets.FileInput(attrs={"accept": "json"}),
    )

    def __init__(self, *args, **kwargs):
        self.field_order = (
            (
                "experiment",
                "meta_analysis_for",
                "replaces",
                "licence",
            )
            + self.FIELD_ORDER
            + (
                "score_data",
                "count_data",
                "relaxed_ordering",
                "meta_data",
                "data_usage_policy",
            )
        )
        # If an experiment is passed in we can used to it to seed initial
        # replaces and m2m field selections.
        self.experiment = None
        self.targetseq = None
        self.allow_aa_sequence = False
        if "experiment" in kwargs:
            self.experiment = kwargs.pop("experiment")
        super().__init__(*args, **kwargs)

        if "sra_ids" in self.fields:
            self.fields.pop("sra_ids")

        if self.instance.pk is not None:
            self.dataset_columns = self.instance.dataset_columns.copy()
            # Disable further uploads if this instance is being processed.
            if (
                "score_data" in self.fields
                and self.instance.processing_state == constants.processing
            ):
                self.fields["score_data"].disabled = True
            if (
                "count_data" in self.fields
                and self.instance.processing_state == constants.processing
            ):
                self.fields["count_data"].disabled = True
        else:
            # This will be used later after score/count files have been read in
            # to store the headers.
            self.dataset_columns = {
                constants.score_columns: [],
                constants.count_columns: [],
            }

        self.fields["abstract_text"].help_text = (
            "A plain text or markdown abstract relating to the scoring "
            "method used for this score set. Click the preview button "
            "to view a rendered preview of what other users will "
            "see once you publish your submission."
        )
        self.fields["method_text"].help_text = (
            "A plain text or markdown method describing the scoring "
            "method used for this score set. Click the preview button "
            "to view a rendered preview of what other users will "
            "see once you publish your submission."
        )

        self.fields["short_description"].max_length = 500

        if not self.editing_existing:
            self.fields["meta_analysis_for"] = forms.ModelMultipleChoiceField(
                queryset=ScoreSet.objects.none(),
                required=False,
                widget=forms.SelectMultiple(
                    attrs={"class": "form-control select2"},
                ),
            )
            self.fields["experiment"] = forms.ModelChoiceField(
                queryset=Experiment.objects.none(),
                required=False,
                empty_label="--------",
                widget=forms.Select(attrs={"class": "form-control select2"}),
            )
            self.fields["replaces"] = forms.ModelChoiceField(
                queryset=ScoreSet.objects.none(),
                required=False,
                empty_label="--------",
                widget=forms.Select(attrs={"class": "form-control select2"}),
            )

            self.fields["experiment"].required = False
            self.fields["meta_analysis_for"].required = False
            self.fields["replaces"].required = False

            self.set_replaces_options()
            self.set_experiment_options()
            self.set_meta_analysis_options()
        else:
            # Do not allow editing after the fact. Makes tracking parent
            # changes difficult, especially for meta-analyses.
            self.fields.pop("experiment", None)
            self.fields.pop("meta_analysis_for", None)
            self.fields.pop("replaces", None)

        self.fields["licence"] = forms.ModelChoiceField(
            queryset=Licence.objects.all(),
            initial=Licence.get_default(),
            required=False,
            empty_label="--------",
            widget=forms.Select(
                attrs={"class": "form-control select2"},
                choices=self.__class__.format_licence_options(),
            ),
        )

        self.set_initial_keywords()
        self.set_initial_dois()
        self.set_initial_pmids()

    # ----------------------- SETUP CONFIG ------------------------- #
    @staticmethod
    def format_licence_options():
        choices = [("", "--------")]
        for licence in Licence.objects.all():
            name = licence.get_long_name()
            if licence == Licence.get_default():
                name += " [Default]"
            choices.append((licence.pk, name))
        return choices

    def set_initial_keywords(self):
        if self.experiment is not None and self.instance.pk is None:
            self.fields["keywords"].initial = self.experiment.keywords.all()

    def set_initial_dois(self):
        if self.experiment is not None and self.instance.pk is None:
            self.fields["doi_ids"].initial = self.experiment.doi_ids.all()

    def set_initial_pmids(self):
        if self.experiment is not None and self.instance.pk is None:
            self.fields[
                "pubmed_ids"
            ].initial = self.experiment.pubmed_ids.all()

    def set_meta_analysis_options(self):
        if "meta_analysis_for" in self.fields:
            # Remove scoreset options which are already a meta analysis
            options = (
                (
                    ScoreSet.objects.all()
                    if settings.META_ANALYSIS_ALLOW_DAISY_CHAIN
                    else ScoreSet.non_meta_analyses()
                )
                .exclude(private=True)
                .exclude(pk=self.instance.pk)
                .exclude(urn=self.instance.urn)
                .order_by("urn")
            )

            self.fields["meta_analysis_for"].queryset = options
            choices = [
                (
                    s.pk,
                    "{} | {} (meta)".format(s.urn, s.title)
                    if s.is_meta_analysis
                    else "{} | {}".format(s.urn, s.title),
                )
                for s in options.all()
            ]
            self.fields["meta_analysis_for"].widget.choices = choices

    def set_replaces_options(self):
        if "replaces" in self.fields:
            admin_instances = self.user.profile.administrator_scoresets()
            editor_instances = self.user.profile.editor_scoresets()
            choices = set(
                [i.pk for i in admin_instances.union(editor_instances)]
            )
            if self.experiment is not None:
                choices &= set([i.pk for i in self.experiment.scoresets.all()])
            elif self.instance.parent is not None:
                choices &= set(
                    [i.pk for i in self.instance.parent.scoresets.all()]
                )
            scoresets_qs = (
                ScoreSet.objects.filter(pk__in=choices)
                .exclude(private=True)
                .exclude(pk=self.instance.pk)
                .exclude(urn=self.instance.urn)
                .order_by("urn")
            )
            self.fields["replaces"].queryset = scoresets_qs

            fmt_options = [("", self.fields["replaces"].empty_label)] + [
                (s.pk, "{} | {}".format(s.urn, s.title))
                for s in scoresets_qs.all()
            ]
            self.fields["replaces"].widget.choices = fmt_options

    def set_experiment_options(self):
        if "experiment" in self.fields:
            admin_instances = self.user.profile.administrator_experiments()
            editor_instances = self.user.profile.editor_experiments()
            public_instances = Experiment.objects.filter(private=False)
            choices = set(
                [
                    i.pk
                    for i in (
                        admin_instances | editor_instances | public_instances
                    ).distinct()
                ]
            )

            # Prevent attaching a regular score set to a meta-analysis
            # experiment
            experiment_qs = (
                Experiment.non_meta_analyses()
                .filter(pk__in=choices)
                .order_by("urn")
            )
            self.fields["experiment"].queryset = experiment_qs

            fmt_options = [("", self.fields["experiment"].empty_label)] + [
                (e.pk, "{} | {}".format(e.urn, e.title))
                for e in experiment_qs.all()
            ]
            self.fields["experiment"].widget.choices = fmt_options

            if self.experiment is not None:
                choices_qs = Experiment.objects.filter(
                    pk__in=[self.experiment.pk]
                ).order_by("urn")
                self.fields["experiment"].queryset = choices_qs
                self.fields["experiment"].widget.choices = (
                    (
                        self.experiment.pk,
                        "{} | {}".format(
                            self.experiment.urn, self.experiment.title
                        ),
                    ),
                )
                self.fields["experiment"].initial = self.experiment

    # -------------------- CLEANING ---------------------- #
    def clean_meta_analysis_for(self):
        if self.editing_existing:
            raise ValidationError(ErrorMessages.MetaAnalysis.changing_children)

        children = (
            self.cleaned_data.get("meta_analysis_for", ScoreSet.objects.none())
            or ScoreSet.objects.none()
        )

        if children.count() == 0:
            return children

        if (
            children.count() > 0
            and self.data.get("experiment", None) is not None
        ):
            raise ValidationError(
                ErrorMessages.MetaAnalysis.experiment_present
            )

        for child in children:
            if child.private:
                raise ValidationError(
                    ErrorMessages.MetaAnalysis.linking_private
                )
            if (
                child.is_meta_analysis
                and not settings.META_ANALYSIS_ALLOW_DAISY_CHAIN
            ):
                raise ValidationError(
                    ErrorMessages.MetaAnalysis.linking_other_meta
                )

        return children

    def clean_experiment(self):
        if self.editing_existing:
            raise ValidationError(ErrorMessages.Experiment.changing_experiment)
        if self.is_meta_analysis:
            return self.get_meta_analysis_experiment()
        return self.cleaned_data.get("experiment", None)

    def clean_replaces(self):
        replaces = self.cleaned_data.get("replaces", None)
        experiment = self.data.get("experiment", None)
        if experiment is not None and str(experiment).strip() != "":
            experiment = int(experiment)

        if self.editing_existing:
            raise ValidationError(ErrorMessages.Replaces.changing_replaces)

        if replaces is not None:
            if self.is_meta_analysis and (not replaces.is_meta_analysis):
                raise ValidationError(
                    ErrorMessages.Replaces.meta_replacing_non_meta
                )
            if (not self.is_meta_analysis) and replaces.is_meta_analysis:
                raise ValidationError(
                    ErrorMessages.Replaces.non_meta_replacing_meta
                )

            if (
                replaces.next_version is not None
                and replaces.next_version != self.instance
            ):
                raise ValidationError(
                    ErrorMessages.Replaces.already_replaced.format(
                        replaces.urn
                    )
                )

            if replaces.private:
                raise ValidationError(ErrorMessages.Replaces.is_not_public)

            if replaces.pk == self.instance.pk:
                raise ValidationError(ErrorMessages.Replaces.replacing_self)

            if experiment != replaces.experiment.pk:
                raise ValidationError(
                    ErrorMessages.Replaces.different_experiment
                )

        return replaces

    def clean_licence(self):
        licence = self.cleaned_data.get("licence", None)
        if not licence:
            licence = Licence.get_default()
        return licence

    def clean_score_data(self) -> MaveDataset:
        score_file = self.cleaned_data.get("score_data", None)
        if not score_file:
            return MaveDataset()

        v = MaveDataset.for_scores(file=score_file)
        v.validate(targetseq=self.targetseq, relaxed_ordering=True)

        if v.is_valid:
            self.dataset_columns[constants.score_columns] = v.non_hgvs_columns
            return v
        else:
            if v.n_errors <= self.MAX_ERRORS:
                for error in v.errors:
                    self.add_error("score_data", mark_safe(error))
            else:
                self.add_error(
                    "score_data",
                    "Scores file contains errors. Download the errors file to "
                    "see details.",
                )
            return v

    def clean_count_data(self) -> MaveDataset:
        count_file = self.cleaned_data.get("count_data", None)
        if not count_file:
            self.dataset_columns[constants.count_columns] = []
            return MaveDataset()

        v = MaveDataset.for_counts(file=count_file)
        v.validate(targetseq=self.targetseq, relaxed_ordering=True)

        if v.is_valid:
            self.dataset_columns[constants.count_columns] = v.non_hgvs_columns
            return v
        else:
            if v.n_errors <= self.MAX_ERRORS:
                for error in v.errors:
                    self.add_error("count_data", mark_safe(error))
            else:
                self.add_error(
                    "count_data",
                    "Counts file contains errors. Download the errors file to "
                    "see details.",
                )
            return v

    def clean_meta_data(self):
        meta_file = self.cleaned_data.get("meta_data", None)
        if meta_file is None:
            return {}
        try:

            if isinstance(meta_file, InMemoryUploadedFile):
                content = meta_file.read()
                if isinstance(content, bytes):
                    content = content.decode()
                meta_file = io.StringIO(content)

            dict_ = json.load(meta_file)
            return dict_
        except ValueError as error:
            raise ValidationError(
                ErrorMessages.MetaData.incorrect_format.format(error)
            )

    def clean(self):
        cleaned_data = super().clean()
        if self._errors:
            # There are errors, maybe from the `clean_<field_name>` methods.
            # End here and run the parent method to quickly return the form.
            return cleaned_data

        if not self.editing_existing:
            if not (
                self.is_meta_analysis or cleaned_data.get("experiment", None)
            ):
                self.add_error(
                    None,
                    "Please select an Experiment or create a meta-analysis.",
                )

        # Indicates that a new scoreset is being created or a failed scoreset
        # is being edited. Failed scoresets have no variants.
        if getattr(self, "edit_mode", False):
            scores_required = False
        else:
            scores_required = (
                self.instance.pk is None
                or not self.instance.has_variants
                or self.instance.processing_state == constants.failed
            )

        score_data: MaveDataset = cleaned_data.get("score_data")
        count_data: MaveDataset = cleaned_data.get("count_data")

        if score_data and count_data:
            self.allow_aa_sequence = (
                score_data.index_column == constants.hgvs_pro_column
                and count_data.index_column == constants.hgvs_pro_column
            )

        meta_data = cleaned_data.get("meta_data", {})

        has_score_data = (score_data is not None) and (not score_data.is_empty)
        has_count_data = (count_data is not None) and (not count_data.is_empty)
        has_meta_data = (meta_data is not None) and len(meta_data) > 0

        if has_meta_data:
            self.instance.extra_metadata = meta_data

        # In edit mode, we have relaxed the requirement of uploading a score
        # dataset since one already exists.
        if scores_required and not has_score_data:
            self.add_error(
                None if "score_data" not in self.fields else "score_data",
                ErrorMessages.ScoreData.score_file_required,
            )
            return cleaned_data

        # In edit mode if a user tries to submit a new count dataset without
        # an accompanying score dataset, this error will be thrown. We could
        # relax this but there is the potential that the user might upload
        # a new count dataset and forget to upload a new score dataset.
        if has_count_data and not has_score_data:
            self.add_error(
                None if "score_data" not in self.fields else "score_data",
                ErrorMessages.CountData.no_score_file,
            )
            return cleaned_data

        if has_count_data and not score_data.match_other(count_data):
            self.add_error(
                None if "count_data" not in self.fields else "count_data",
                ErrorMessages.CountData.different_variants,
            )
            return cleaned_data

        # Re-build the variants if any new files have been processed.
        # If has_count_data is true then has_score_data is also be true because
        # uploading counts alone is not allowed. The reverse is not always true.
        if has_score_data:
            validate_scoreset_json(self.dataset_columns)
            if not has_count_data:
                count_data = MaveDataset()
            variants = {
                "scores_df": score_data.data(serializable=True),
                "counts_df": count_data.data(serializable=True),
                "index": score_data.index_column,
            }
            cleaned_data["variants"] = variants

        return cleaned_data

    def is_valid(self, targetseq: Optional[str] = None):
        # Set as instance variables so full clean will be called every time
        # a new sequence or other settings are passed in.
        self.targetseq = targetseq

        # Clear previous errors to trigger full_clean call in base class.
        self._errors = None
        return super().is_valid()

    # --------------- SAVING ------------------------------------ #
    @transaction.atomic
    def _save_m2m(self):
        return super()._save_m2m()

    @transaction.atomic
    def save(self, commit=True):
        if self.is_meta_analysis and commit:
            if not (self.editing_public or self.editing_existing):
                experiment: Experiment = self.cleaned_data["experiment"]

                if experiment.created_by is None:
                    experiment.set_created_by(self.user, propagate=False)
                if experiment.modified_by is None:
                    experiment.set_modified_by(self.user, propagate=False)

                experiment.save()

                experiment_set: ExperimentSet = experiment.experimentset
                if experiment_set.created_by is None:
                    experiment_set.set_created_by(self.user, propagate=False)
                if experiment_set.modified_by is None:
                    experiment_set.set_modified_by(self.user, propagate=False)

                experiment_set.save()

                self.instance.experiment = experiment
                self.instance.experiment_id = experiment.id

        return super().save(commit=commit)

    # ---------------------- PUBLIC ----------------------------- #
    def serialize_variants(self):
        """Serializes variants in JSON format."""
        variants = self.cleaned_data.get("variants", {})
        scores_df = variants.get("scores_df", pd.DataFrame())
        counts_df = variants.get("counts_df", pd.DataFrame())
        index = variants.get("index", None)
        return scores_df, counts_df, index

    def has_variants(self):
        return bool(self.cleaned_data.get("variants", {}))

    @property
    def should_write_scores_error_file(self):
        validator = self.cleaned_data.get("score_data", MaveDataset())
        return validator and validator.n_errors > self.MAX_ERRORS

    @property
    def should_write_counts_error_file(self):
        validator = self.cleaned_data.get("count_data", MaveDataset())
        return validator and validator.n_errors > self.MAX_ERRORS

    @property
    def is_meta_analysis(self):
        if "meta_analysis_for" not in self.fields:
            return self.instance.is_meta_analysis
        else:
            return len(self.meta_analysis_form_field_data) > 0

    def get_existing_meta_analysis(self) -> Optional[ScoreSet]:
        children = self.meta_analysis_form_field_data
        if len(children) < 1:
            return None

        field_name, objects = ScoreSet.annotate_meta_children_count()
        # Keep all meta-analysis score sets which contain exactly the number
        # of child score sets the user is trying to link to.
        meta_analyses = objects.filter(**{f"{field_name}": len(children)})
        for id_ in children:
            # Filter out any meta-analyses which do not have the exact same
            # child score sets. Ordering is not important.
            meta_analyses = meta_analyses.filter(meta_analysis_for=id_)
        return meta_analyses.first()

    def get_meta_analysis_experiment(self) -> Experiment:
        existing = self.get_existing_meta_analysis()
        children = ScoreSet.objects.filter(
            id__in=self.meta_analysis_form_field_data
        )

        if children.count() == 0:
            raise ValueError(
                "Form data indicates non-meta-analysis, "
                "but caller implies form is for a meta-analysis."
            )

        # Create a new experiment but linked to the child's experimentset
        # if this is a novel meta-analysis
        experimentset = None
        all_from_same_experiment_set = (
            len(set([c.experiment.experimentset.urn for c in children.all()]))
            == 1
        )
        if all_from_same_experiment_set:
            experimentset = children.first().experiment.experimentset

        # Create new parent tree if this is a completely novel meta-analysis
        description = ", ".join([s.urn for s in children.order_by("urn")])
        if existing is None:
            return Experiment(
                title=f"Meta-analysis of {description}",
                short_description=f"Meta-analysis of {description}",
                experimentset=experimentset,
            )

        return existing.experiment

    @property
    def editing_existing(self):
        return self.instance.pk is not None

    @property
    def editing_public(self):
        return not self.instance.private

    @property
    def meta_analysis_form_field_data(self):
        children = self.data.get("meta_analysis_for", [])
        if isinstance(children, (int, str)):
            children = [children]
        return children


class ScoreSetEditForm(ScoreSetForm):
    """
    Subset of the `ScoreSetForm`, which freezes all fields except `private`,
    `doi_id`, `keywords`, `abstract` and `method_desc`. Only these fields
    are editable.
    """

    class Meta(ScoreSetForm.Meta):
        model = ScoreSet

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.edit_mode = True

        # Might already be popped if passing in instance
        self.fields.pop("experiment", None)
        self.fields.pop("meta_analysis_for", None)
        self.fields.pop("replaces", None)

        self.fields.pop("score_data")
        self.fields.pop("count_data")
        self.fields.pop("meta_data")

        if self.instance is not None:
            if self.user not in self.instance.administrators:
                self.fields.pop("data_usage_policy")
