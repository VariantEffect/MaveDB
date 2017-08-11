
import math
import numpy as np
from io import StringIO

import django.forms as forms
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

from .models import ScoreSet, Variant, SCORES_KEY, COUNTS_KEY
from .validators import (
    valid_scoreset_count_data_input, valid_scoreset_score_data_input,
    valid_scoreset_json, valid_variant_json, Constants
)


class ScoreSetForm(forms.ModelForm):

    scores_data = forms.CharField(
        required=True, label="Scores data",
        help_text="Comma separated fields.",
        validators=[valid_scoreset_score_data_input]
    )
    counts_data = forms.CharField(
        required=True, label="Counts data",
        help_text="Comma separated fields.",
        validators=[valid_scoreset_count_data_input]
    )

    class Meta:
        model = ScoreSet
        fields = (
            'experiment',
            'private',
            'abstract',
            'method_desc',
            'doi_id',
            'metadata',
        )

    def save_variants(self):
        if self.is_bound and self.is_valid():
            variants = self.cleaned_data["variants"]
            for var in variants:
                var.scoreset = self.instance
                var.save()

    def cached_variants(self):
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
        data_columns = {
            SCORES_KEY: [xs.strip() for xs in scores_header],
            COUNTS_KEY: [xs.strip() for xs in counts_header]
        }
        valid_scoreset_json(data_columns)
        cleaned_data['data_columns'] = data_columns
        scores_data.close()
        counts_data.close()
        return cleaned_data

    def _validate_rows_create_variants(self, cleaned_data=None):
        if not cleaned_data:
            cleaned_data = super(ScoreSetForm, self).clean()
        data_columns = cleaned_data.get('data_columns', [])
        scores_header = data_columns[SCORES_KEY]
        counts_header = data_columns[COUNTS_KEY]
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
                        "Scores row %(row)s contains less columns than those "
                        "in the header"
                    ),
                    params={"row": i}
                )
            if len(score_line) > len(scores_header):
                raise ValidationError(
                    _(
                        "Scores row %(row)s contains more columns than those "
                        "in the header"
                    ),
                    params={"row": i}
                )
            if len(count_line) < len(counts_header):
                raise ValidationError(
                    _(
                        "Counts row %(row)s contains less columns than those "
                        "in the header"
                    ),
                    params={"row": i}
                )
            if len(count_line) > len(counts_header):
                raise ValidationError(
                    _(
                        "Counts row %(row)s contains more columns than those "
                        "in the header"
                    ),
                    params={"row": i}
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

            if processed_score_line[0] != processed_count_line[0]:
                raise ValidationError(
                    _(
                        "The hgvs strings within the scores dataset do "
                        "not match those within the counts dataset. Ensure "
                        "counts data set and scores data set contain the "
                        "same variants in the same order. Also ensure that "
                        "the hgvs column is always first."
                    )
                )

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
                    _("Row %(row)s in scores data has non-numeric values"),
                    params={"row": ','.join(processed_score_line[1:])}
                )
            if not all(counts_are_floats):
                raise ValidationError(
                    _("Row %(row)s in counts data has non-numeric values"),
                    params={"row": ','.join(processed_count_line[1:])}
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

        cleaned_data['variants'] = variants
        return cleaned_data

    def clean(self):
        if self.errors:
            return super(ScoreSetForm, self).clean()
        cleaned_data = super(ScoreSetForm, self).clean()
        self._validate_scores_counts_same_rows(cleaned_data)
        cleaned_data = self._validate_and_create_headers(cleaned_data)
        cleaned_data = self._validate_rows_create_variants(cleaned_data)
        return cleaned_data

    def save(self, commit=True):
        super(ScoreSetForm, self).save(commit=commit)
        self.instance.data_columns = self.cleaned_data["data_columns"]
        variants = self.cleaned_data["variants"]
        if commit:
            self.instance.save()
            for var in variants:
                var.scoreset = self.instance
                var.save()
        return self.instance
