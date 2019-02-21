import json
import io
from enum import Enum

import pandas as pd

from django import forms as forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.translation import ugettext

from core.mixins import NestedEnumMixin
from core.utilities import readable_null_values

from main.models import Licence

from variant.validators import validate_variant_rows

from dataset import constants as constants
from ..forms.base import DatasetModelForm
from ..models.experiment import Experiment
from ..models.scoreset import ScoreSet
from ..validators import (
    validate_scoreset_score_data_input,
    validate_csv_extension, validate_json_extension,
    validate_scoreset_count_data_input,
    validate_scoreset_json,
    validate_datasets_define_same_variants,
)


class ErrorMessages(NestedEnumMixin, Enum):
    """ScoreSet field specific error messages."""
    class Field(Enum):
        invalid_choice = ugettext(
            forms.ModelChoiceField.default_error_messages['invalid_choice']
        )
        
    class Experiment(Enum):
        public_scoreset = ugettext(
            "Changing the parent Experiment of "
            "a public score set is not supported."
        )
    
    class Replaces(Enum):
        different_experiment = ugettext(
            "Replaces field selection must be a member of the "
            "selected experiment."
        )
        already_replaced = ugettext("{} has already been replaced.")
        is_not_public = ugettext("Only public entries can be replaced.")
        replacing_self = ugettext("A score set cannot replace itself.")
    
    class MetaData(Enum):
        incorrect_format = ugettext("Incorrectly formatted json file: {}")
        
    class ScoreData(Enum):
        score_file_required = ugettext(
            "You must upload a non-empty scores data file.")
        no_variants = ugettext(
            'No variants could be parsed from your input file. '
            'Please upload a non-empty file.'
        )
    
    class CountData(Enum):
        no_score_file = ugettext(
            "You must upload an accompanying score data file when "
            "uploading a new count data file or replacing an "
            "existing one."
        )
        no_variants = ugettext(
            'No variants could be parsed from your input file. '
            'Please upload a non-empty file.'
        )
        primary_mismatch = ugettext(
            "The primary hgvs column inferred from the scores file ('{}') does"
            "not match that inferred from the counts file ('{}'). This can "
            "if the two files do not define the same variants across rows."
        )
        different_variants = ugettext(
            "Scores and counts files must define the same variants. "
            "Check that the hgvs columns in both files match "
            "(order insensitive)."
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
            'data_usage_policy',
            'replaces',
        )

    score_data = forms.FileField(
        required=False, label="Variant score data",
        help_text=(
            "A valid CSV file containing variant score information. "
            "The file must at least specify the columns 'hgvs_nt' or 'hgvs_pro' "
            "(or both) and 'score'. There are no constraints on other column "
            "names. Apart from the 'hgvs' column, all data must be numeric.\n\n"
            "Row scores that are empty, whitespace or the strings {} "
            "(case-insensitive) will be converted to a null score. The columns "
            "'hgvs_nt' and 'hgvs_pro' must define the same variants as those in "
            "the count file below."
        ).format(', '.join(readable_null_values)),
        validators=[
            validate_scoreset_score_data_input, validate_csv_extension],
        widget=forms.widgets.FileInput(attrs={"accept": "csv"})
    )
    count_data = forms.FileField(
        required=False, label="Variant count data",
        help_text=(
            "A valid CSV file containing variant count information. " 
            "The file must at least specify the column 'hgvs_nt' or 'hgvs_pro' "
            "(or both) and one additional column containing numeric count data. "
            "There are no constraints on the other column names.\n\n"
            "Row counts that are empty, whitepace or any of the strings {} "
            "(case-insensitive) will be converted to a null score. The columns "
            "'hgvs_nt' and 'hgvs_pro' must define the same variants as those in "
            "the score file above."
        ).format(', '.join(readable_null_values)),
        validators=[
            validate_scoreset_count_data_input, validate_csv_extension],
        widget=forms.widgets.FileInput(attrs={"accept": "csv"})
    )
    meta_data = forms.FileField(
        required=False, label="Metadata",
        help_text=(
            "You can upload a JSON file containing additional information "
            "not available as a field in this form."
        ),
        validators=[validate_json_extension],
        widget=forms.widgets.FileInput(attrs={"accept": "json"})
    )

    def __init__(self, *args, **kwargs):
        self.field_order = ('experiment', 'replaces', 'licence',
                            'data_usage_policy') + \
                           self.FIELD_ORDER + \
                           ('score_data', 'count_data', 'meta_data',)
        # If an experiment is passed in we can used to it to seed initial
        # replaces and m2m field selections.
        self.experiment = None
        if 'experiment' in kwargs:
            self.experiment = kwargs.pop('experiment')
        super().__init__(*args, **kwargs)
        
        if 'sra_ids' in self.fields:
            self.fields.pop("sra_ids")

        if self.instance.pk is not None:
            self.dataset_columns = self.instance.dataset_columns.copy()
            # Disable further uploads if this instance is being processed.
            if 'score_data' in self.fields and \
                    self.instance.processing_state == constants.processing:
                self.fields['score_data'].disabled = True
            if 'count_data' in self.fields and \
                    self.instance.processing_state == constants.processing:
                self.fields['count_data'].disabled = True
        else:
            # This will be used later after score/count files have been read in
            # to store the headers.
            self.dataset_columns = {
                constants.score_columns: [],
                constants.count_columns: [],
            }

        self.fields['abstract_text'].help_text = (
            "A plain text or markdown abstract relating to the scoring "
            "method used for this score set. Click the preview button "
            "to view a rendered preview of what other users will "
            "see once you publish your submission."
        )
        self.fields['method_text'].help_text = (
            "A plain text or markdown method describing the scoring "
            "method used for this score set. Click the preview button "
            "to view a rendered preview of what other users will "
            "see once you publish your submission."
        )

        self.fields['short_description'].max_length = 500
        self.fields['experiment'] = forms.ModelChoiceField(
            queryset=None, required=True, widget=forms.Select(
                attrs={"class": "form-control"}))
        self.fields['replaces'] = forms.ModelChoiceField(
            queryset=ScoreSet.objects.none(), required=False,
            widget=forms.Select(
                attrs={"class": "form-control"}))
        self.fields['licence'] = forms.ModelChoiceField(
            queryset=Licence.objects.all(), required=False,
            widget=forms.Select(
                attrs={"class": "form-control "}))

        self.fields["replaces"].required = False
        self.set_replaces_options()
        self.set_experiment_options()
        
        self.set_initial_keywords()
        self.set_initial_dois()
        self.set_initial_pmids()
        
        self.fields["licence"].required = False
        if not self.fields["licence"].initial:
            self.fields["licence"].initial = Licence.get_default()

        choices = [("", '--------')]
        for licence in Licence.objects.all():
            name = licence.get_long_name()
            if licence == Licence.get_default():
                name += ' [Default]'
            choices.append((licence.pk, name))
        self.fields['licence'].widget.choices = choices

        for field in ('licence', 'replaces', 'experiment'):
            if field in self.fields:
                self.fields[field].widget.attrs.update(**{'class': 'select2'})
   
    def clean_experiment(self):
        experiment = self.cleaned_data['experiment']
        existing_experiment = self.instance.parent
        if self.instance.pk is not None and existing_experiment is not None:
            if experiment is not None:
                if existing_experiment.urn != experiment.urn and \
                        not self.instance.private:
                    raise ValidationError(
                        ErrorMessages.Experiment.public_scoreset
                    )
                if existing_experiment.urn != experiment.urn and \
                        self.instance.private:
                    # Replaces will need to be reset if changing experiments
                    # because a scoreset being replaces must be a member
                    # of the same experiment.
                    self.instance.replaces = None
                    # Re-trigger clean replaces to make sure the selected
                    # replaces is a member of the same experiment.
                    self.cleaned_data['replaces'] = self.clean_replaces()
        return experiment

    def clean_licence(self):
        licence = self.cleaned_data.get("licence", None)
        if not licence:
            licence = Licence.get_default()
        return licence

    def clean_replaces(self):
        replaces = self.cleaned_data.get("replaces", None)
        experiment = self.cleaned_data.get("experiment", None)
        if replaces is not None:
            if experiment is not None and \
                    replaces not in experiment.scoresets.all():
                raise ValidationError(
                    ErrorMessages.Replaces.different_experiment)
            if replaces.next_version is not None and \
                    replaces.next_version != self.instance:
                raise ValidationError(
                    ErrorMessages.Replaces.already_replaced.format(replaces.urn)
                )
            if replaces.private:
                raise ValidationError(ErrorMessages.Replaces.is_not_public)
            if replaces.pk == self.instance.pk:
                raise ValidationError(ErrorMessages.Replaces.replacing_self)
        return replaces

    def clean_score_data(self):
        score_file = self.cleaned_data.get("score_data", None)
        if not score_file:
            return pd.DataFrame(), None
        non_hgvs_columns, primary_hgvs_column, score_df = \
            validate_variant_rows(score_file)
        self.dataset_columns[constants.score_columns] = non_hgvs_columns
        return score_df, primary_hgvs_column

    def clean_count_data(self):
        count_file = self.cleaned_data.get("count_data", None)
        if not count_file:
            self.dataset_columns[constants.count_columns] = []
            return pd.DataFrame(), None
        non_hgvs_columns, primary_column, counts_df = \
            validate_variant_rows(count_file)
        self.dataset_columns[constants.count_columns] = non_hgvs_columns
        return counts_df, primary_column

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

        # Indicates that a new scoreset is being created or a failed scoreset
        # is being edited. Failed scoresets have not variants.
        if getattr(self, 'edit_mode', False):
            scores_required = False
        else:
            scores_required = self.instance.pk is None or \
                              not self.instance.has_variants or \
                              self.instance.processing_state == constants.failed

        score_data, primary_hgvs_scores = cleaned_data.get(
            "score_data", (pd.DataFrame(), None))
        count_data, primary_hgvs_counts = cleaned_data.get(
            "count_data", (pd.DataFrame(), None))
        meta_data = cleaned_data.get("meta_data", {})

        has_score_data = len(score_data) > 0
        has_count_data = len(count_data) > 0
        has_meta_data = len(meta_data) > 0

        if has_meta_data:
            self.instance.extra_metadata = meta_data

        # In edit mode, we have relaxed the requirement of uploading a score
        # dataset since one already exists.
        if scores_required and not has_score_data:
            self.add_error(
                None if 'score_data' not in self.fields else 'score_data',
                ErrorMessages.ScoreData.score_file_required
            )
            return cleaned_data

        # In edit mode if a user tries to submit a new count dataset without
        # an accompanying score dataset, this error will be thrown. We could
        # relax this but there is the potential that the user might upload
        # a new count dataset and forget to upload a new score dataset.
        if has_count_data and not has_score_data:
            self.add_error(
                None if 'score_data' not in self.fields else 'score_data',
                ErrorMessages.CountData.no_score_file
            )
            return cleaned_data
        
        if has_count_data:
            try:
                validate_datasets_define_same_variants(
                    scores=score_data,
                    counts=count_data,
                )
            except ValidationError:
                self.add_error(
                    None if 'count_data' not in self.fields else 'count_data',
                    ErrorMessages.CountData.different_variants
                )
                return cleaned_data
            
        # Re-build the variants if any new files have been processed.
        # If has_count_data is true then has_score_data should also be true.
        # The reverse is not always true.
        if has_score_data:
            validate_scoreset_json(self.dataset_columns)
            if not has_count_data:
                count_data = pd.DataFrame()
            variants = {
                'scores_df': score_data,
                'counts_df': count_data,
                'index': primary_hgvs_scores,
            }
            cleaned_data["variants"] = variants
            
        return cleaned_data

    @transaction.atomic
    def _save_m2m(self):
        return super()._save_m2m()

    @transaction.atomic
    def save(self, commit=True):
        return super().save(commit=commit)

    def serialize_variants(self):
        """Serializes variants in JSON format."""
        variants = self.cleaned_data.get('variants', {})
        scores_df = variants.get('scores_df', pd.DataFrame())
        counts_df = variants.get('counts_df', pd.DataFrame())
        index = variants.get('index', None)
        return scores_df, counts_df, index
        
    def has_variants(self):
        return bool(self.cleaned_data.get('variants', {}))

    def set_initial_keywords(self):
        if self.experiment is not None and self.instance.pk is None:
            self.fields['keywords'].initial = self.experiment.keywords.all()

    def set_initial_dois(self):
        if self.experiment is not None and self.instance.pk is None:
            self.fields['doi_ids'].initial = self.experiment.doi_ids.all()

    def set_initial_pmids(self):
        if self.experiment is not None and self.instance.pk is None:
            self.fields['pubmed_ids'].initial = self.experiment.pubmed_ids.all()
        
    def set_replaces_options(self):
        if 'replaces' in self.fields:
            admin_instances = self.user.profile.administrator_scoresets()
            editor_instances = self.user.profile.editor_scoresets()
            choices = set(
                [i.pk for i in admin_instances.union(editor_instances)]
            )
            if self.experiment is not None:
                choices &= set(
                    [i.pk for i in self.experiment.scoresets.all()]
                )
            elif self.instance.parent is not None:
                choices &= set(
                    [i.pk for i in self.instance.parent.scoresets.all()]
                )
            scoresets_qs = ScoreSet.objects\
                .filter(pk__in=choices)\
                .exclude(private=True)\
                .exclude(pk=self.instance.pk)\
                .exclude(urn=self.instance.urn)\
                .order_by("urn")
            self.fields["replaces"].queryset = scoresets_qs
            self.fields["replaces"].widget.choices = \
                [("", self.fields["replaces"].empty_label)] + [
                (s.pk, '{} | {}'.format(s.urn, s.title))
                for s in scoresets_qs.all()
            ]

    def set_experiment_options(self):
        if 'experiment' in self.fields:
            admin_instances = self.user.profile.administrator_experiments()
            editor_instances = self.user.profile.editor_experiments()
            choices = set(
                [i.pk for i in admin_instances.union(editor_instances)]
            )
            experiment_qs = Experiment.objects.filter(
                pk__in=choices).order_by("urn")
            self.fields["experiment"].queryset = experiment_qs
            self.fields["experiment"].widget.choices = \
                [("", self.fields["experiment"].empty_label)] + [
                (e.pk, '{} | {}'.format(e.urn, e.title))
                for e in experiment_qs.all()
            ]
            
            if self.experiment is not None:
                choices_qs = Experiment.objects.filter(
                    pk__in=[self.experiment.pk]).order_by("urn")
                self.fields["experiment"].queryset = choices_qs
                self.fields['experiment'].widget.choices = (
                    (self.experiment.pk, '{} | {}'.format(
                        self.experiment.urn, self.experiment.title)),
                )
                self.fields["experiment"].initial = self.experiment

    @classmethod
    def from_request(cls, request, instance=None, prefix=None, initial=None):
        form = super().from_request(request, instance, prefix, initial)
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
        self.fields.pop('meta_data')
        self.fields.pop('replaces')

        if self.instance is not None:
            if self.user not in self.instance.administrators:
                self.fields.pop('data_usage_policy')
