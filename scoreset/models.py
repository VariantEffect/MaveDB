
import numpy as np
import logging
import datetime

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.db import IntegrityError
from django.db.models.signals import post_save
from django.dispatch import receiver

from main.utils.pandoc import convert_md_to_html
from main.models import Keyword
from experiment.models import Experiment

from .validators import (
    valid_scs_accession, valid_var_accession,
    valid_scoreset_json, valid_hgvs_string, valid_variant_json
)

COUNTS_KEY = "counts"
SCORES_KEY = "scores"
logger = logging.getLogger("django")
positive_integer_validator = MinValueValidator(limit_value=0)


class ScoreSet(models.Model):
    """
    This is the class representing a set of scores for an experiment.
    The ScoreSet object houses all information relating to a particular
    method of variant scoring. This class assumes that all validation
    was handled at the form level, and as such performs no additonal
    validation and will raise IntegreityError if there's bad input.

    Parameters
    ----------
    accession : `models.CharField`
        The accession in the format 'SCSXXXXXX[A-Z]+'
    experiment : `models.ForeignKey`, required.
        The experiment a scoreset is assciated with. Cannot be null.
    creation_date : `models.DataField`
        Data of instantiation in yyyy-mm-dd format.
    approved : `models.BooleanField`
        The approved status, as seen by the database admin. Instances are
        created by default as not approved and must be manually checked
        before going live.
    last_used_suffix : `models.IntegerField`
        Min value of 0. Counts how many variants have been associated with
        this dataset. Must be manually incremented everytime, but this might
        change to a post_save signal
    private : `models.BooleanField`
        Whether the dataset should be private and viewable only by
        those approved in the permissions.
    dataset_columns : `models.JSONField`
        A JSON instances with keys `scores` and `counts`. The values are
        lists of strings indicating the columns to be expected in the variants
        for this dataset.
    abstract : `models.TextField`
        A markdown text blob.
    method_desc : `models.TextField`
        A markdown text blob of the scoring method.
    doi_id : `models.CharField`
        The DOI for this scoreset if any.
    metadata : `models.JSONField`
        The free-form json metadata that might be associated with this
        experiment
    keywords : `models.ManyToManyField`
        The keyword instances that are associated with this instance.
    """
    # ---------------------------------------------------------------------- #
    #                       Class members/functions
    # ---------------------------------------------------------------------- #
    ACCESSION_DIGITS = 6
    ACCESSION_PREFIX = "SCS"

    class Meta:
        ordering = ['-creation_date']
        verbose_name = "ScoreSet"
        verbose_name_plural = "ScoreSets"

    # ---------------------------------------------------------------------- #
    #                       Required Model fields
    # ---------------------------------------------------------------------- #
    accession = models.CharField(
        unique=True, default=None, blank=False, null=True, max_length=64,
        verbose_name="Accession", validators=[valid_scs_accession])

    experiment = models.ForeignKey(
        to=Experiment, on_delete=models.PROTECT, null=False, default=None)

    creation_date = models.DateField(
        blank=False, null=False, default=datetime.date.today,
        verbose_name="Creation date")

    approved = models.BooleanField(
        blank=False, null=False, default=False, verbose_name="Approved")

    last_used_suffix = models.IntegerField(
        default=0, validators=[positive_integer_validator])

    private = models.BooleanField(
        blank=False, null=False, default=True, verbose_name="Private")

    dataset_columns = JSONField(
        verbose_name="Dataset columns", default=dict({
            SCORES_KEY: ['hgvs'],
            COUNTS_KEY: ['hgvs']
        }),
        validators=[valid_scoreset_json]
    )

    # ---------------------------------------------------------------------- #
    #                       Optional Model fields
    # ---------------------------------------------------------------------- #
    # TODO add the following many2many fields:
    # keywords
    abstract = models.TextField(
        blank=True, default="", verbose_name="Abstract")
    method_desc = models.TextField(
        blank=True, default="", verbose_name="Method description")
    doi_id = models.CharField(
        blank=True, default="", verbose_name="DOI identifier", max_length=256)
    metadata = JSONField(blank=True, default={}, verbose_name="Metadata")
    keywords = models.ManyToManyField(Keyword)

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    # TODO: add helper functions to check permision bit and author bits
    def __str__(self):
        return "ScoreSet({}, {}, {}, {})".format(
            str(self.accession),
            str(self.creation_date),
            str(self.dataset_columns),
            str(self.metadata)
        )

    def save(self, *args, **kwargs):
        super(ScoreSet, self).save(*args, **kwargs)
        if not self.accession:
            parent = self.experiment
            middle_digits = parent.accession[-parent.ACCESSION_DIGITS:]
            digit_suffix = parent.next_scoreset_suffix()
            accession = '{}.{}'.format(
                parent.accession.replace(
                    parent.ACCESSION_PREFIX, self.ACCESSION_PREFIX),
                digit_suffix
            )
            parent.last_used_suffix = digit_suffix
            parent.save()
            self.accession = accession
            self.save()

    def next_variant_suffix(self):
        return self.last_used_suffix + 1

    def validate_variant_data(self, variant):
        if variant.scores_columns != self.scores_columns:
            raise ValueError("Variant scores columns '{}' do not match "
                             "ScoreSet columns '{}'.".format(
                                 variant.scores_columns, self.scores_columns))
        if variant.counts_columns != self.counts_columns:
            raise ValueError("Variant counts columns '{}' do not match "
                             "ScoreSet columns '{}'.".format(
                                 variant.counts_columns, self.counts_columns))

    @property
    def scores_columns(self) -> set:
        return set(self.dataset_columns[SCORES_KEY])

    @property
    def counts_columns(self) -> set:
        return set(self.dataset_columns[COUNTS_KEY])

    def md_abstract(self) -> str:
        return convert_md_to_html(self.abstract)

    def md_method_desc(self) -> str:
        return convert_md_to_html(self.method_desc)


class Variant(models.Model):
    """
    This is the class representing an individual variant belonging to one
    and only one ScoreSet instance. The numerical parameters of a variant
    are held in a JSONField, which can be easily queried and extended as
    needed.

    Parameters
    ----------
    accession : `str`
        The accession of the variant. Auto-assigned based off the associated
        scoreset.
    creation_date : `models.DateField`
        The data the variant was created in yyyy-mm-dd format.
    hgvs_string : `str`, required.
        The HGVS string belonging to the variant.
    scoreset : `ScoreSet`, required.
        The associated scoreset of the instance.
    data : `JSONField`
        The variant's numerical data.
    """
    # ---------------------------------------------------------------------- #
    #                       Class members/functions
    # ---------------------------------------------------------------------- #
    ACCESSION_DIGITS = 6
    ACCESSION_PREFIX = "SCSVAR"

    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Variant"
        verbose_name_plural = "Variants"

    # ---------------------------------------------------------------------- #
    #                       Required Model fields
    # ---------------------------------------------------------------------- #
    accession = models.CharField(
        unique=True, default=None, blank=False, null=True, max_length=64,
        verbose_name="Accession", validators=[valid_var_accession])

    creation_date = models.DateField(
        blank=False, null=False, default=datetime.date.today,
        verbose_name="Creation date")

    hgvs = models.TextField(
        blank=False, null=False, default=None, validators=[valid_hgvs_string])

    scoreset = models.ForeignKey(
        to=ScoreSet, on_delete=models.PROTECT, null=False, default=None)

    # ---------------------------------------------------------------------- #
    #                      Optional Model fields
    # ---------------------------------------------------------------------- #
    data = JSONField(
        verbose_name="Data columns", default=dict({
            SCORES_KEY: {'hgvs': None},
            COUNTS_KEY: {'hgvs': None}
        }),
        validators=[valid_variant_json]
    )

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    def __str__(self):
        return "Variant({}, {}, {})".format(
            str(self.accession),
            str(self.creation_date),
            str(self.data)
        )

    @property
    def scores_columns(self) -> set:
        return set(self.data[SCORES_KEY].keys())

    @property
    def counts_columns(self) -> set:
        return set(self.data[COUNTS_KEY].keys())

    @property
    def get_ordered_scores_data(self):
        columns = self.scoreset.scores_columns
        data = [self.data[SCORES_KEY][key] for key in columns]
        return data

    @property
    def get_ordered_counts_data(self):
        columns = self.scoreset.counts_columns
        data = [self.data[COUNTS_KEY][key] for key in columns]
        return data

    def save(self, *args, **kwargs):
        super(Variant, self).save(*args, **kwargs)
        if not self.accession:
            parent = self.scoreset
            digit_suffix = parent.next_variant_suffix()
            accession = '{}.{}'.format(
                parent.accession.replace(
                    parent.ACCESSION_PREFIX, self.ACCESSION_PREFIX),
                digit_suffix
            )
            parent.last_used_suffix = digit_suffix
            parent.save()
            self.accession = accession
            self.save()
