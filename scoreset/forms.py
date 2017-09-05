
import math
import numpy as np
from io import StringIO

import django.forms as forms
from django.dispatch import receiver
from django.db.models import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

from main.utils.query_parsing import parse_query
from main.models import Keyword
from main.fields import ModelSelectMultipleField

from .models import ScoreSet, Variant, SCORES_KEY, COUNTS_KEY
from .validators import (
    valid_scoreset_count_data_input, valid_scoreset_score_data_input,
    valid_scoreset_json, valid_variant_json, Constants
)


class ScoreSetForm(forms.ModelForm):
    """
    Docstring
    """
    class Meta:
        model = ScoreSet
        fields = (
            'experiment',
            'replaces',
            'private',
            'keywords',
            'doi_id',
            'abstract',
            'method_desc',
        )

    scores_data = forms.CharField(
        required=True, label="Scores data",
        help_text="Comma separated fields.",
        validators=[valid_scoreset_score_data_input],
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "style": "height:250px;width:100%"
            }
        )
    )
    counts_data = forms.CharField(
        required=True, label="Counts data",
        help_text="Comma separated fields.",
        validators=[valid_scoreset_count_data_input],
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "style": "height:250px;width:100%"
            }
        )
    )

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

    def __init__(self, *args, **kwargs):
        super(ScoreSetForm, self).__init__(*args, **kwargs)

        if "replaces" in self.fields:
            self.fields["replaces"].required = False

        self.fields["private"].widget = forms.CheckboxInput(
            attrs={
                "class": "form-control",
            }
        )
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
        # a class variable at import time.
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

    def clean(self):
        if self.errors:
            return super(ScoreSetForm, self).clean()
        cleaned_data = super(ScoreSetForm, self).clean()

        has_counts = self.fields.get("counts_data", None) is not None
        has_scores = self.fields.get("scores_data", None) is not None
        if has_counts and has_scores:
            self._validate_scores_counts_same_rows(cleaned_data)
            dataset_columns = self._validate_and_create_headers(cleaned_data)
            variants = self._validate_rows_and_create_variants(
                dataset_columns, cleaned_data
            )
            cleaned_data["dataset_columns"] = dataset_columns
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

        has_counts = self.fields.get("counts_data", None) is not None
        has_scores = self.fields.get("scores_data", None) is not None
        if has_counts and has_scores:
            self.instance.dataset_columns = \
                self.cleaned_data["dataset_columns"]
            self.save_variants()
            for var in self.get_variants():
                var.scoreset = self.instance
                var.save()

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

    def save_variants(self):
        if self.is_bound and self.is_valid():
            variants = self.cleaned_data["variants"]
            for var in variants:
                var.scoreset = self.instance
                var.save()

    def get_variants(self):
        if self.is_bound and self.is_valid():
            return self.cleaned_data['variants']

    def _validate_scores_counts_same_rows(self, cleaned_data=None):
        if not cleaned_data:
            cleaned_data = super(ScoreSetForm, self).clean()

        scores_data = StringIO(cleaned_data[Constants.SCORES_DATA])
        counts_data = StringIO(cleaned_data[Constants.COUNTS_DATA])
        scores_rows = len(scores_data.readlines())
        counts_rows = len(counts_data.readlines())
        if scores_rows != counts_rows:
            scores_data.close()
            counts_data.close()
            raise ValidationError(
                _(
                    "Scores dataset and counts dataset differ in the "
                    "number of rows."
                )
            )
        scores_data.close()
        counts_data.close()

    def _validate_and_create_headers(self, cleaned_data=None):
        if not cleaned_data:
            cleaned_data = super(ScoreSetForm, self).clean()

        scores_data = StringIO(cleaned_data[Constants.SCORES_DATA])
        counts_data = StringIO(cleaned_data[Constants.COUNTS_DATA])
        scores_header = [
            h.strip().lower()
            for h in scores_data.readline().strip().split(',')
        ]
        counts_header = [
            h.strip().lower()
            for h in counts_data.readline().strip().split(',')
        ]
        dataset_columns = {
            SCORES_KEY: [xs.strip() for xs in scores_header],
            COUNTS_KEY: [xs.strip() for xs in counts_header]
        }
        valid_scoreset_json(dataset_columns)
        scores_data.close()
        counts_data.close()
        return dataset_columns

    def _validate_rows_and_create_variants(
            self, dataset_columns, cleaned_data=None):
        if not cleaned_data:
            cleaned_data = super(ScoreSetForm, self).clean()
        scores_header = dataset_columns[SCORES_KEY]
        counts_header = dataset_columns[COUNTS_KEY]
        variants = []

        scores_data = StringIO(cleaned_data[Constants.SCORES_DATA])
        counts_data = StringIO(cleaned_data[Constants.COUNTS_DATA])
        iterator = enumerate(zip(scores_data, counts_data))

        for i, (scores_line, counts_line) in iterator:
            if i == 0:
                continue
            score_line = [x.strip() for x in scores_line.strip().split(',')]
            count_line = [x.strip() for x in counts_line.strip().split(',')]

            if len(score_line) < len(scores_header):
                raise ValidationError(
                    _(
                        "Scores row '%(row)s' contains less columns than "
                        "those in the header."
                    ),
                    params={"row": ','.join([str(x) for x in score_line])}
                )
            if len(score_line) > len(scores_header):
                raise ValidationError(
                    _(
                        "Scores row '%(row)s' contains more columns than "
                        "those in the header."
                    ),
                    params={"row": ','.join([str(x) for x in score_line])}
                )
            if len(count_line) < len(counts_header):
                raise ValidationError(
                    _(
                        "Counts row '%(row)s' contains less columns than "
                        "those in the header."
                    ),
                    params={"row": ','.join([str(x) for x in count_line])}
                )
            if len(count_line) > len(counts_header):
                raise ValidationError(
                    _(
                        "Counts row '%(row)s' contains more columns than "
                        "those in the header."
                    ),
                    params={"row": ','.join([str(x) for x in count_line])}
                )

            processed_score_line = []
            for col_value in score_line:
                try:
                    col_value = float(col_value)
                    if not math.isfinite(col_value):
                        col_value = None
                except (TypeError, ValueError):
                    if col_value.lower() in Constants.NAN_COL_VALUES:
                        col_value = None
                processed_score_line.append(col_value)

            processed_count_line = []
            for col_value in count_line:
                try:
                    col_value = float(col_value)
                    if not math.isfinite(col_value):
                        col_value = None
                except (TypeError, ValueError):
                    if col_value.lower() in Constants.NAN_COL_VALUES:
                        col_value = None
                processed_count_line.append(col_value)

            # Check if the hgvs entries are the same in both datasets.
            if processed_score_line[0] != processed_count_line[0]:
                raise ValidationError(
                    _(
                        "The hgvs strings within the Scores data input do "
                        "not match those within Counts data input. Ensure "
                        "counts data set and scores data set contain the "
                        "same variants in the same order. Also ensure that "
                        "the hgvs column is always first."
                    )
                )

            # Check if the hgvs entries are the same in both datasets.
            scores_are_floats = (
                isinstance(value, float)
                for value in processed_score_line[1:]
                if value is not None
            )
            counts_are_floats = (
                isinstance(value, float)
                for value in processed_count_line[1:]
                if value is not None
            )
            if not all(scores_are_floats):
                raise ValidationError(
                    _(
                        "Row '%(row)s' in the Scores data input contains "
                        "non-numeric values."
                    ),
                    params={"row": ','.join(
                        [str(x) for x in processed_score_line]
                    )}
                )
            if not all(counts_are_floats):
                raise ValidationError(
                    _(
                        "Row '%(row)s' in the Counts data input contains "
                        "non-numeric values."
                    ),                    params={"row": ','.join(
                        [str(x) for x in processed_count_line]
                    )}
                )

            if not all(d is None for d in processed_score_line[1:]) or \
                    not all(d is None for d in processed_count_line[1:]):
                scores_json = {
                    k: v for k, v in zip(scores_header, processed_score_line)
                }
                counts_json = {
                    k: v for k, v in zip(counts_header, processed_count_line)
                }
                # Store hgvs string and the json object
                hgvs = processed_score_line[0]
                data = {SCORES_KEY: scores_json, COUNTS_KEY: counts_json}
                valid_variant_json(data)
                var = Variant(scoreset=self.instance, hgvs=hgvs, data=data)
                variants.append(var)

        return variants


class ScoreSetEditForm(ScoreSetForm):
    """
    Docstring
    """
    scores_data = None
    counts_data = None
    experiment = None
    replaces = None

    class Meta:
        model = ScoreSet
        fields = (
            'private',
            'doi_id',
            'keywords',
            'abstract',
            'method_desc'
        )
