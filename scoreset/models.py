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
    accession : `str`
        This is the only required field, and should be specified at all points
        of instantiation (Experiment, Experiment.objects.create).

    Methods
    -------
    build_accession
        Creates a new accession but taking the digit bit from the associated
        :py:class:`ExperimentSet` and adding an alphabetaical character based
        on the number of experiments in the set.
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
            SCORES_KEY: ['score', 'SE'],
            COUNTS_KEY: ['count']
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
    doi_id = models.TextField(
        blank=True, default="", verbose_name="DOI identifier")
    metadata = JSONField(blank=True, default={}, verbose_name="Metadata")

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    # TODO: add helper functions to check permision bit and author bits
    def __str__(self):
        return "ScoreSet({}, {}, {}, {})".format(
            str(self.accession),
            str(self.experiment),
            str(self.creation_date),
            str(self.dataset_columns))

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
    hgvs_string : `str`
        The HGVS string belonging to the variant.
    scoreset : `ScoreSet`
        The associated scoreset of the instance.
    data : `JSONField`
        The variant's numerical data.

    Methods
    -------
    save
        Overrides the save from `models.Model` to create an
        accession after the base save method is called.
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

    hgvs_string = models.TextField(
        blank=False, null=False, default=None, validators=[valid_hgvs_string])

    scoreset = models.ForeignKey(
        to=ScoreSet, on_delete=models.PROTECT, null=False, default=None)

    # ---------------------------------------------------------------------- #
    #                      Optional Model fields
    # ---------------------------------------------------------------------- #
    data = JSONField(
        verbose_name="Data columns", default=dict({
            SCORES_KEY: {'score': [None], 'SE': [None]},
            COUNTS_KEY: {'count': [None]}
        }),
        validators=[valid_variant_json]
    )

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    def __str__(self):
        return "Variant({}, {}, {}, {})".format(
            str(self.accession),
            str(self.creation_date),
            str(self.scoreset),
            str(self.data))

    @property
    def scores_columns(self) -> set:
        return set(self.data[SCORES_KEY].keys())

    @property
    def counts_columns(self) -> set:
        return set(self.data[COUNTS_KEY].keys())

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
