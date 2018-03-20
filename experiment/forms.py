import math

import django.forms as forms
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

from main.utils.query_parsing import parse_query
from main.models import Licence

from .fields import ModelSelectMultipleField
from .models import Keyword, TargetOrganism, SraAccession, PubmedAccession, DoiAccession
from .models import Experiment, ScoreSet, Variant, ExperimentSet
from .models import DatasetModel, AccessionModel, ExternalAccession

from .validators import (
    valid_scoreset_count_data_input, valid_scoreset_score_data_input,
    valid_scoreset_json, valid_variant_json, Constants, valid_hgvs_string,
    csv_validator
)


class DatasetModelForm(forms.ModelForm):
    """
    Base form handling the fields present in :class:`.models.DatasetModel`
    """
    class Meta:
        model = DatasetModel
        fields = (
            'abstract_text',
            'method_text',
            'keywords',
            'sra_accessions',
            'doi_accessions',
            'pmid_accessions'
        )
        widgets = {
            'abstract_text': forms.Textarea(attrs={"class": "form-control"}),
            'method_text': forms.Textarea(attrs={"class": "form-control"}),
            'keywords': ModelSelectMultipleField(
                klass=Keyword, to_field_name='text', required=False,
                widget=forms.widgets.SelectMultiple(
                    attrs={"class": "form-control select2 select2-token-select"}
                )
            ),
            'sra_accessions': ModelSelectMultipleField(
                klass=Keyword, to_field_name='resource_accession', required=False,
                widget=forms.widgets.SelectMultiple(
                    attrs={"class": "form-control select2 select2-token-select"}
                )
            ),
            'doi_accessions': ModelSelectMultipleField(
                klass=Keyword, to_field_name='resource_accession', required=False,
                widget=forms.widgets.SelectMultiple(
                    attrs={"class": "form-control select2 select2-token-select"}
                )
            ),
            'pmid_accessions': ModelSelectMultipleField(
                klass=Keyword, to_field_name='resource_accession', required=False,
                widget=forms.widgets.SelectMultiple(
                    attrs={"class": "form-control select2 select2-token-select"}
                )
            )
        }

    def __init__(self, *args, **kwargs):
        super(DatasetModelForm).__init__(*args, **kwargs)
        self.fields["keywords"].queryset = Keyword.objects.all()
        self.fields["sra_accessions"].queryset = SraAccession.objects.all()
        self.fields["doi_accessions"].queryset = DoiAccession.objects.all()
        self.fields["pubmed_accessions"].queryset = PubmedAccession.objects.all()


class ExperimentForm(DatasetModelForm):
    """
    Docstring
    """
    class Meta(DatasetModel.Meta):
        model = Experiment
        fields = (
            'experimentset',
            'target',
            'wt_sequence'
        )

    def __init__(self, *args, **kwargs):
        super(ExperimentForm, self).__init__(*args, **kwargs)
        if "experimentset" in self.fields:
            self.fields["experimentset"].widget = forms.widgets.Select(
                attrs={"style": 'width:20%;'}
            )
        self.fields["target"].widget = forms.TextInput(
            attrs={
                "class": "form-control",
            }
        )
        self.fields["wt_sequence"].widget = forms.Textarea(
            attrs={
                "class": "form-control",
                "style": "height:250px;width:100%"
            }
        )

        self.fields["target_organism"] = ModelSelectMultipleField(
            klass=TargetOrganism,
            text_key="text",
            queryset=None,
            required=False,
            widget=forms.widgets.Select(
                attrs={
                    "class": "form-control select2 select2-token-select",
                    "style": "width:50%;height:auto;"
                }
            )
        )
        self.fields["target_organism"].queryset = TargetOrganism.objects.all()


    def save(self, commit=True):
        super(ExperimentForm, self).save(commit=commit)
        if commit:
            self.process_and_save_all()
        else:
            self.save_m2m = self.process_and_save_all
        return self.instance

    def process_and_save_all(self):
        """
        This will saved all changes made to the instance. Keywords not
        present in the form submission will be removed, new keywords will
        be created in the database and all keywords in the upload form will
        be added to the instance's keyword m2m field.
        """
        if not (self.is_bound and self.is_valid()):
            return None
        if self.errors:
            raise ValueError(
                "The %s could not be %s because the data didn't validate." % (
                    self.instance._meta.object_name,
                    'created' if self.instance._state.adding else 'changed',
                )
            )

        self.instance.save()

        if "keywords" in self.fields:
            self.save_new_m2m("keywords")
            self.instance.update_keywords(
                self.all_m2m("keywords")
            )
        if "external_accessions" in self.fields:
            self.save_new_m2m("external_accessions")
            self.instance.update_external_accessions(
                self.all_m2m("external_accessions")
            )
        if "target_organism" in self.fields:
            self.save_new_m2m("target_organism")
            self.instance.update_target_organism(
                self.all_m2m("target_organism")
            )

        self.instance.save()
        return self.instance

    def save_new_m2m(self, field_name):
        """
        Save new m2m instances that were created during the clean process.
        """
        if self.is_bound and self.is_valid():
            for instance in self.new_m2m(field_name):
                instance.save()

    def new_m2m(self, field_name):
        """
        Return a list of keywords that were created during the clean process.
        """
        if field_name not in self.fields:
            raise ValueError(
                '{} is not a field in this form.'.format(field_name)
            )
        return self.fields[field_name].new_instances

    def all_m2m(self, field_name):
        """
        Return a list of all keywords found during the cleaning process
        """
        if self.is_bound and self.is_valid():
            not_new = [i for i in self.cleaned_data.get(field_name, [])]
            new = self.new_m2m(field_name)
            return new + not_new

    @classmethod
    def PartialFormFromRequest(cls, request, instance):
        if request.method == "POST":
            form = cls(data=request.POST, instance=instance)
        else:
            form = cls(instance=instance)
        form.fields.pop("experimentset")
        return form


class ExperimentEditForm(ExperimentForm):
    """
    A subset of `ExperimentForm` for editiing instances. Follows the same
    logic as `ExperimentForm`
    """
    experimentset = None
    target = None
    wt_sequence = None

    class Meta:
        model = Experiment
        fields = (
            'experimentset',  # excluded
            'target',  # excluded
            'target_organism',  # excluded
            'wt_sequence',  # excluded
            'sra_id',
            'doi_id',
            'keywords',
            'external_accessions',
            'abstract',
            'method_desc',
        )

    def __init__(self, *args, **kwargs):
        super(ExperimentEditForm, self).__init__(*args, **kwargs)
        self.fields.pop('target_organism')
        self.fields.pop('target')
        self.fields.pop('wt_sequence')
        self.fields.pop('experimentset')


# --------------------------------------------------------------------------- #
#                           ScoreSet Form
# --------------------------------------------------------------------------- #
class ScoreSetForm(forms.ModelForm):
    """
    This form is presented on the create new scoreset view. It contains
    all the validation logic required to ensure that a score dataset and
    counts dataset are parsed into valid Variant objects that are associated
    with the created scoreset. It also defines additional validation for
    the `replaces` field in scoreset to make sure that the selected
    `ScoreSet` is a member of the selected `Experiment` instance.
    """
    class Meta:
        model = ScoreSet
        fields = (
            'experiment',
            'replaces',
            'licence_type',
            'keywords',
            'doi_id',
            'abstract',
            'method_desc',
        )

    scores_data = forms.FileField(
        required=True, label="Score data",
        validators=[valid_scoreset_score_data_input, csv_validator],
        widget=forms.widgets.FileInput(attrs={"accept": "csv"})
    )
    counts_data = forms.FileField(
        required=False, label="Count data",
        validators=[valid_scoreset_count_data_input, csv_validator],
        widget=forms.widgets.FileInput(attrs={"accept": "csv"})
    )

    def __init__(self, *args, **kwargs):
        super(ScoreSetForm, self).__init__(*args, **kwargs)
        self.dataset_columns = {
            Constants.SCORES_KEY: [], Constants.COUNTS_KEY: []
        }
        self.scores_json = {}
        self.counts_json = {}

        if "replaces" in self.fields:
            self.fields["replaces"].required = False
            self.fields["replaces"].widget = forms.widgets.Select(
                attrs={"style": 'width:20%;'}
            )
        if "experiment" in self.fields:
            self.fields["experiment"].widget = forms.widgets.Select(
                attrs={"style": 'width:20%;'}
            )
        if "licence_type" in self.fields:
            if not self.fields["licence_type"].initial:
                self.fields["licence_type"].initial = Licence.get_default()
            self.fields["licence_type"].empty_label = None

        self.fields["doi_id"].widget = forms.TextInput(
            attrs={
                "class": "form-control",
            }
        )
        self.fields["abstract"].widget = forms.Textarea(
            attrs={
                "class": "form-control",
                "style": "height:250px;width:100%"
            }
        )
        self.fields["method_desc"].widget = forms.Textarea(
            attrs={
                "class": "form-control",
                "style": "height:250px;width:100%"
            }
        )

        # This needs to be in `__init__` because otherwise it is created as
        # a class variable at import time. This happens because django
        # won't defer loading of custom fields.
        self.fields["keywords"] = ModelSelectMultipleField(
            klass=Keyword,
            text_key="text",
            queryset=None,
            required=False,
            widget=forms.widgets.SelectMultiple(
                attrs={
                    "class": "form-control select2 select2-token-select",
                    "style": "width:100%;height:50px;"
                }
            )
        )
        self.fields["keywords"].queryset = Keyword.objects.all()

    def clean_licence_type(self):
        licence = self.cleaned_data.get("licence_type", None)
        if not licence:
            licence = Licence.objects.get(short_name="CC BY-NC-SA 4.0")
        return licence

    def clean_replaces(self):
        scoreset = self.cleaned_data.get("replaces", None)
        experiment = self.cleaned_data.get("experiment", None)
        if scoreset is not None and experiment is not None:
            if scoreset not in experiment.scoreset_set.all():
                raise ValidationError(
                    _(
                        "Replaces field selection must be a member of the "
                        "selected experiment."
                    )
                )
        return scoreset

    def clean_scores_data(self):
        scores_file = self.cleaned_data.get("scores_data", None)
        if not scores_file and self.fields["scores_data"].required:
            raise ValidationError(
                _("Score data field is required.")
            )
        if not scores_file:
            self.dataset_columns[Constants.SCORES_KEY] = []
            return None

        scores_file.seek(0)
        header_line = scores_file.readline()
        if isinstance(header_line, bytes):
            header_line = header_line.decode()
        scores_header = [
            h.strip().lower()
            for h in header_line.strip().split(',')
        ]
        if Constants.HGVS_COLUMN not in scores_header:
            raise ValidationError(
                _("Score data is missing the required column '%(hgvs)s'"),
                params={"hgvs": Constants.HGVS_COLUMN}
            )
        self.dataset_columns[Constants.SCORES_KEY] = scores_header

        # Parse each line of the file after parsing out the header.
        for line in scores_file.readlines():
            if isinstance(line, bytes):
                line = line.decode()
            if not line.strip():
                continue

            parsed_line = parse_query(line)
            if len(parsed_line) != len(scores_header):
                raise ValidationError(
                    _(
                        "The number of columns in '%(row)s' from Score data "
                        "does not match those in the header."
                    ),
                    params={"row": ','.join(parsed_line)}
                )

            # Attempt to parse all column values into floats where appropriate
            processed_score_line = []
            for col_value in parsed_line:
                try:
                    col_value = float(col_value)
                    if not math.isfinite(col_value):
                        col_value = None
                except (TypeError, ValueError):
                    if col_value.lower() in Constants.NAN_COL_VALUES:
                        col_value = None
                processed_score_line.append(col_value)

            # Values not in NAN_COL_VALUES aren't touched. If any exist
            # After the previous step, throw a non-numeric error.
            scores_are_floats = (
                isinstance(value, float)
                for value in processed_score_line[1:]
                if value is not None
            )
            if not all(scores_are_floats):
                raise ValidationError(
                    _(
                        "Row '%(row)s' in the Score data input contains "
                        "non-numeric values."
                    ),
                    params={"row": ','.join(
                        [str(x) for x in processed_score_line]
                    )}
                )

            # Create a dictionary where k is the header column and
            # v is the corresponding value. This will be used later for
            # variant construction.
            scores_json = {}
            if not all(d is None for d in processed_score_line[1:]):
                scores_json = {
                    k: v for k, v in zip(scores_header, processed_score_line)
                }
                hgvs = processed_score_line[0]
                valid_hgvs_string(hgvs)
                if hgvs in self.scores_json:
                    raise ValidationError(
                        _(
                            "HGVS identifier '%(hgvs)s' in Score data appears "
                            "more than once."
                        ),
                        params={"hgvs": hgvs}
                    )
                self.scores_json[hgvs] = scores_json

        return scores_file

    def clean_counts_data(self):
        counts_file = self.cleaned_data.get("counts_data", None)
        if not counts_file:
            self.dataset_columns[Constants.COUNTS_KEY] = []
            return None

        counts_file.seek(0)
        header_line = counts_file.readline()
        if isinstance(header_line, bytes):
            header_line = header_line.decode()
        counts_header = [
            h.strip().lower()
            for h in header_line.strip().split(',')
        ]
        if Constants.HGVS_COLUMN not in counts_header:
            raise ValidationError(
                _("Count data is missing the required column '%(hgvs)s'"),
                params={"hgvs": Constants.HGVS_COLUMN}
            )
        self.dataset_columns[Constants.COUNTS_KEY] = counts_header

        # Parse each line of the file after parsing out the header.
        for line in counts_file.readlines():
            if isinstance(line, bytes):
                line = line.decode()
            if not line.strip():
                continue
            parsed_line = parse_query(line)
            if len(parsed_line) != len(counts_header):
                raise ValidationError(
                    _(
                        "The number of columns in '%(row)s' from Count data "
                        "does not match those in the header."
                    ),
                    params={"row": ','.join(parsed_line)}
                )

            # Attempt to parse all column values into floats where appropriate
            processed_line = []
            for col_value in parsed_line:
                try:
                    col_value = float(col_value)
                    if not math.isfinite(col_value):
                        col_value = None
                except (TypeError, ValueError):
                    if col_value.lower() in Constants.NAN_COL_VALUES:
                        col_value = None
                processed_line.append(col_value)

            # Values not in NAN_COL_VALUES aren't touched. If any exist
            # After the previous step, throw a non-numeric error.
            counts_are_floats = (
                isinstance(value, float)
                for value in processed_line[1:]
                if value is not None
            )
            if not all(counts_are_floats):
                raise ValidationError(
                    _(
                        "Row '%(row)s' in the Count data input contains "
                        "non-numeric values."
                    ),
                    params={"row": ','.join(
                        [str(x) for x in processed_line]
                    )}
                )

            # Create a dictionary where k is the header column and
            # v is the corresponding value. This will be used later for
            # variant construction.
            counts_json = {}
            if not all(d is None for d in processed_line[1:]):
                counts_json = {
                    k: v for k, v in zip(counts_header, processed_line)
                }
                hgvs = processed_line[0]
                valid_hgvs_string(hgvs)
                if hgvs in self.counts_json:
                    raise ValidationError(
                        _(
                            "HGVS identifier '%(hgvs)s' in Count data appears"
                            " more than once."
                        ),
                        params={"hgvs": hgvs}
                    )
                self.counts_json[hgvs] = counts_json
        return counts_file

    def clean(self):
        if self.errors:
            return super(ScoreSetForm, self).clean()
        cleaned_data = super(ScoreSetForm, self).clean()
        has_scores = cleaned_data.get("scores_data", None) is not None
        has_counts = cleaned_data.get("counts_data", None) is not None

        if not has_scores and not hasattr(self, "edit_mode"):
            scores_required = self.fields["scores_data"].required
            if scores_required:
                raise ValidationError(
                    _(
                        "Score data cannot be empty/must contain at least one"
                        " row with non-null values"
                    )
                )

        if has_counts and not has_scores:
            raise ValidationError(
                _(
                    "You must upload an accompanying Score data file with "
                    "a Count data file."
                )
            )

        if has_scores:
            valid_scoreset_json(self.dataset_columns, has_counts)
            cleaned_data["dataset_columns"] = self.dataset_columns

            # For every hgvs in scores but not in counts, fill in the
            # counts columns (if a counts dataset is supplied) with null values
            for hgvs, scores_json in list(self.scores_json.items()):
                if has_counts and hgvs not in self.counts_json:
                    counts_json = {"hgvs": hgvs}
                    for col in self.dataset_columns[Constants.COUNTS_KEY]:
                        if not col == Constants.HGVS_COLUMN:
                            counts_json[col] = None
                    self.counts_json[hgvs] = counts_json

            # For every hgvs in counts but not in scores, fill in the
            # scores columns with null values
            for hgvs, counts_json in list(self.counts_json.items()):
                if hgvs not in self.scores_json:
                    scores_json = {"hgvs": hgvs}
                    for col in self.dataset_columns[Constants.SCORES_KEY]:
                        if not col == Constants.HGVS_COLUMN:
                            scores_json[col] = None
                    self.scores_json[hgvs] = scores_json

            variants = []
            hgvs_ls = set(self.scores_json.keys()) | set(
                self.counts_json.keys())
            for hgvs in hgvs_ls:
                scores_json = self.scores_json[hgvs]
                counts_json = self.counts_json[hgvs] if has_counts else {}
                data = {Constants.SCORES_KEY: scores_json, Constants.COUNTS_KEY: counts_json}
                valid_variant_json(data)
                var = Variant(scoreset=self.instance, hgvs=hgvs, data=data)
                variants.append(var)

            cleaned_data["variants"] = variants

        return cleaned_data

    def save(self, commit=True):
        super(ScoreSetForm, self).save(commit=commit)
        if commit:
            self.process_and_save_all()
        else:
            self.save_m2m = self.process_and_save_all
        return self.instance

    def process_and_save_all(self):
        """
        This will saved all changes made to the instance. Keywords not
        present in the form submission will be removed, new keywords will
        be created in the database and all keywords in the upload form will
        be added to the instance's keyword m2m field.
        """
        if not (self.is_bound and self.is_valid()):
            return None
        if self.errors:
            raise ValueError(
                "The %s could not be %s because the data didn't validate." % (
                    self.instance._meta.object_name,
                    'created' if self.instance._state.adding else 'changed',
                )
            )

        self.instance.save()
        has_counts = self.cleaned_data.get("counts_data", None) is not None
        has_scores = self.cleaned_data.get("scores_data", None) is not None
        if has_counts or has_scores:
            self.save_variants_and_set_dataset_columns()
        self.save_new_keywords()
        self.instance.update_keywords(self.all_keywords())
        self.instance.save()
        return self.instance

    def save_new_keywords(self):
        """
        Save new keywords that were created during the clean process.
        """
        if self.is_bound and self.is_valid():
            for kw in self.new_keywords():
                kw.save()

    def new_keywords(self):
        """
        Return a list of keywords that were created during the clean process.
        """
        return self.fields["keywords"].new_instances

    def all_keywords(self):
        """
        Return a list of all keywords found during the cleaning process
        """
        if self.is_bound and self.is_valid():
            not_new = [kw for kw in self.cleaned_data.get("keywords", [])]
            new = self.new_keywords()
            return new + not_new

    @transaction.atomic
    def save_variants_and_set_dataset_columns(self):
        if self.is_bound and self.is_valid():
            variants = self.cleaned_data.get("variants", [])
            if not variants:
                return

            # Delete all the variants and replace with the new ones.
            # Easier to do a full delete than parse each variant to check
            # which ones have changed.
            self.instance.delete_variants()
            for var in variants:
                var.scoreset = self.instance
                var.save()
            self.instance.dataset_columns = self.cleaned_data["dataset_columns"]

    def get_variants(self):
        if self.is_bound and self.is_valid():
            return self.cleaned_data['variants']

    @classmethod
    def PartialFormFromRequest(cls, request, instance):
        if request.method == "POST":
            form = cls(
                data=request.POST, files=request.FILES, instance=instance
            )
        else:
            form = cls(instance=instance)

        form.fields.pop("experiment")
        pks = [
            i.pk for i in request.user.profile.administrator_scoresets()
            if i in instance.experiment.scoreset_set.all() and i != instance
        ]
        scoresets = ScoreSet.objects.filter(
            pk__in=set(pks)).order_by("accession")
        form.fields["replaces"].queryset = scoresets

        for field in form.fields:
            form.fields[field].required = False

        return form


class ScoreSetEditForm(ScoreSetForm):
    """
    Subset of the `ScoreSetForm`, which freezes all fields except `private`,
    `doi_id`, `keywords`, `abstract` and `method_desc`. Only these fields
    are editable.
    """
    scores_data = None
    counts_data = None
    experiment = None
    replaces = None
    licence_type = None

    class Meta:
        model = ScoreSet
        fields = (
            'doi_id',
            'keywords',
            'abstract',
            'method_desc'
        )

    def __init__(self, *args, **kwargs):
        super(ScoreSetEditForm, self).__init__(*args, **kwargs)
        self.edit_mode = True


# --------------------------------------------------------------------------- #
#                              MetaForms
# --------------------------------------------------------------------------- #
class KeywordForm(forms.ModelForm):
    """
    Keyword `ModelForm` to be instantiated with a dictionary or an
    existing instance.
    """
    class Meta:
        model = Keyword
        fields = ("text", )


class ExternalAccessionForm(forms.ModelForm):
    """
    ExternalAccession `ModelForm` to be instantiated with a dictionary or an
    existing instance.
    """
    class Meta:
        model = ExternalAccession
        fields = ("text",)


class TargetOrganismForm(forms.ModelForm):
    """
    TargetOrganism `ModelForm` to be instantiated with a dictionary or an
    existing instance.
    """
    class Meta:
        model = TargetOrganism
        fields = ("text",)
