from io import TextIOWrapper

from django import forms as forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import ugettext

from main.models import Licence

from variant.models import Variant
from variant.validators import validate_variant_rows
from dataset.validators import validate_scoreset_json

from dataset import constants as constants
from ..models.scoreset import ScoreSet
from ..models.experiment import Experiment
from ..forms.base import DatasetModelForm
from ..validators import (
    validate_scoreset_score_data_input,
    validate_csv_extension,
    validate_scoreset_count_data_input
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
    class Meta(DatasetModelForm.Meta):
        model = ScoreSet
        fields = DatasetModelForm.Meta.fields + (
            'experiment',
            'licence',
            'replaces'
        )

    score_data = forms.FileField(
        required=True, label="Variant score data (required)",
        validators=[validate_scoreset_score_data_input, validate_csv_extension],
        widget=forms.widgets.FileInput(attrs={"accept": "csv"})
    )
    count_data = forms.FileField(
        required=False, label="Variant count data (optional)",
        validators=[validate_scoreset_count_data_input, validate_csv_extension],
        widget=forms.widgets.FileInput(attrs={"accept": "csv"})
    )

    def __init__(self, *args, **kwargs):
        super(ScoreSetForm, self).__init__(*args, **kwargs)

        # This will be used later after score/count files have been read in
        # to store the headers.
        self.dataset_columns = {
            constants.score_columns: [],
            constants.count_columns: [],
            constants.metadata_columns: []
        }

        self.fields['experiment'] = forms.ModelChoiceField(
            queryset=None, required=True, widget=forms.Select(
                attrs={"class": "form-control"}))
        self.fields['replaces'] = forms.ModelChoiceField(
            queryset=None, required=False, widget=forms.Select(
                attrs={"class": "form-control"}))
        self.fields['licence'] = forms.ModelChoiceField(
            queryset=Licence.objects.all(), required=False,
            widget=forms.Select(
                attrs={"class": "form-control"}))

        self.fields["replaces"].required = False
        self.set_replaces_options()

        self.set_experiment_options()
        self.fields['experiment'].empty_label = 'Create new experiment'

        self.fields["licence"].required = False
        if not self.fields["licence"].initial:
            self.fields["licence"].initial = Licence.get_default()
        self.fields["licence"].empty_label = 'Default'

    def clean_licence(self):
        licence = self.cleaned_data.get("licence", None)
        if not licence:
            licence = Licence.get_default()
        return licence

    def clean_replaces(self):
        scoreset = self.cleaned_data.get("replaces", None)
        experiment = self.cleaned_data.get("experiment", None)
        if scoreset is not None and experiment is not None:
            if scoreset not in experiment.scoresets.all():
                raise ValidationError(
                    ugettext(
                        "Replaces field selection must be a member of the "
                        "selected experiment."
                    ))
        return scoreset

    def clean_score_data(self):
        score_file = self.cleaned_data.get("score_data", None)
        if not score_file:
            return {}
        # Don't need to wrap this in a try/catch as the form
        # will catch any Validation errors automagically.
        #   Valdator must check the following:
        #       Header has hgvs and at least one other column
        #       Number of rows does not match header
        #       Datatypes of rows match
        #       HGVS string is a valid hgvs string
        #       Hgvs appears more than once in rows
        score_file = TextIOWrapper(score_file, encoding='utf-8')
        header, hgvs_score_map = validate_variant_rows(score_file)
        self.dataset_columns[constants.score_columns] = header
        return hgvs_score_map

    def clean_count_data(self):
        count_file = self.cleaned_data.get("count_data", None)
        if not count_file:
            return {}
        # Don't need to wrap this in a try/catch as the form
        # will catch any Validation errors automagically.
        #   Valdator must check the following:
        #       Header has hgvs and at least one other column
        #       Number of rows does not match header
        #       Datatypes of rows match
        #       HGVS string is a valid hgvs string
        #       Hgvs appears more than once in rows
        count_file = TextIOWrapper(count_file, encoding='utf-8')
        header, hgvs_count_map = validate_variant_rows(count_file)
        self.dataset_columns[constants.count_columns] = header
        return hgvs_count_map

    @staticmethod
    def _fill_in_missing(hgvs_keys, mapping):
        # This function has side-effects - it creates new keys in the default
        # dict `mapping`.
        for key in hgvs_keys:
            _ = mapping[key]
            mapping[key][constants.hgvs_column] = key
        return mapping

    def clean(self):
        if self.errors:
            # There are errors, maybe from the `clean_<field_name>` methods.
            # End here and run the parent method to quickly return the form.
            return super().clean()

        cleaned_data = super().clean()
        score_data_field = self.fields.get("score_data", None)
        scores_required = False if not score_data_field else \
            score_data_field.required

        hgvs_score_map = cleaned_data.get("score_data", {})
        hgvs_count_map = cleaned_data.get("count_data", {})
        hgvs_meta_map = cleaned_data.get("meta_data", {})

        has_score_data = len(hgvs_score_map) > 0
        has_count_data = len(hgvs_count_map) > 0
        has_meta_data = len(hgvs_meta_map) > 0

        # In edit mode, we have relaxed the requirement of uploading a score
        # dataset since one already exists.
        if scores_required and not has_score_data and \
                not hasattr(self, "edit_mode"):
            raise ValidationError(
                ugettext(
                    "Score data cannot be empty and must contain at "
                    "least one row with non-null values"
                )
            )
        # In edit, mode if a user tries to submit a new count dataset without
        # an accompanying score dataset, this error will be thrown. We could
        # relax this but there is the potential that the user might upload
        # a new count dataset and forget to upload a new score dataset.
        if (has_count_data or has_meta_data) and not has_score_data:
            raise ValidationError(
                ugettext(
                    "You must upload an accompanying score data file when "
                    "uploading a new count/meta data file, or replacing an "
                    "existing one."
                )
            )

        # TODO: Handle the cases where count/meta data is not posted
        if has_count_data:
            # For every hgvs in scores but not in counts, fill in the
            # counts columns (if a counts dataset is supplied) with null values
            self._fill_in_missing(hgvs_score_map.keys(), hgvs_count_map)
            # For every hgvs in counts but not in scores, fill in the
            # scores columns with null values.
            self._fill_in_missing(hgvs_count_map.keys(), hgvs_score_map)

        # Re-build the variants if any new files have been processed.
        # If has_count_data is true then has_score_data should also be true.
        # The reverse is not always true.
        if has_score_data:
            validate_scoreset_json(self.dataset_columns)
            variants = dict()

            for hgvs in hgvs_score_map.keys():
                scores_json = hgvs_score_map[hgvs]
                counts_json = hgvs_count_map[hgvs] if has_count_data else {}
                meta_json = hgvs_meta_map[hgvs] if has_meta_data else {}
                data = {
                    constants.variant_score_data: scores_json,
                    constants.variant_count_data: counts_json,
                    constants.variant_metadata: meta_json
                }
                variant = Variant(scoreset=self.instance, hgvs=hgvs, data=data)
                variants[hgvs] = variant

            cleaned_data["variants"] = variants

        return cleaned_data

    def _save_m2m(self):
        variants = self.get_variants()
        if variants:  # No variants if in edit mode and no new files uploaded.
            self.instance.delete_variants()
            for _, variant in variants.items():
                variant.save()
                self.instance.variants.add(variant)
        super()._save_m2m()

    @transaction.atomic
    def save(self, commit=True):
        return super().save(commit=commit)

    def get_variants(self):
        return self.cleaned_data.get('variants', {})

    def set_replaces_options(self):
        if 'replaces' in self.fields:
            choices = self.user.profile.administrator_scoresets() + \
                self.user.profile.contributor_scoresets()
            scoresets_qs = ScoreSet.objects.filter(
                pk__in=set([i.pk for i in choices])).order_by("urn")
            self.fields["replaces"].queryset = scoresets_qs

    def set_experiment_options(self):
        if 'experiment' in self.fields:
            choices = self.user.profile.administrator_experiments() + \
                self.user.profile.contributor_experiments()
            experiment_qs = Experiment.objects.filter(
                pk__in=set([i.pk for i in choices])).order_by("urn")
            self.fields["experiment"].queryset = experiment_qs

    @classmethod
    def from_request(cls, request, instance):
        form = super().from_request(request, instance)
        form.set_replaces_options()
        form.set_experiment_options()
        return form


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
        self.fields.pop('experiment')
        self.fields.pop('score_data')
        self.fields.pop('count_data')
        self.fields.pop('licence')
        self.fields.pop('replaces')