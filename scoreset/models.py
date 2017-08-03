import logging
import datetime

from django.conf import settings
from django.core.validators import MinValueValidator
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
    valid_json_field, valid_hgvs_string
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
        to=Experiment, on_delete=models.PROTECT, null=True, default=None)

    creation_date = models.DateField(
        blank=False, null=False, default=datetime.date.today,
        verbose_name="Creation date")

    approved = models.BooleanField(
        blank=False, null=False, default=False, verbose_name="Approved")

    last_used_suffix = models.IntegerField(
        default=0, validators=[positive_integer_validator])

    private = models.BooleanField(
        blank=False, null=False, default=True, verbose_name="Private")

    # ---------------------------------------------------------------------- #
    #                       Optional Model fields
    # ---------------------------------------------------------------------- #
    # TODO add the following many2many fields:
    # keywords
    # metadata
    abstract = models.TextField(
        blank=True, default="", verbose_name="Abstract")
    method_desc = models.TextField(
        blank=True, default="", verbose_name="Method description")
    doi_id = models.TextField(
        blank=True, default="", verbose_name="DOI identifier")
    dataset_columns = JSONField(
        verbose_name="Dataset columns", default=dict({
            SCORES_KEY: [],
            COUNTS_KEY: []
        }),
        validators=[valid_json_field]
    )

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
        if self.experiment is None:
            raise IntegrityError("Cannot save when experiment is None")
        super(ScoreSet, self).save(*args, **kwargs)
        if self.accession is not None:
            valid_scs_accession(self.accession)
        else:
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
        unique=True, default=None, blank=False, null=False, max_length=64,
        verbose_name="Accession", validators=[valid_var_accession])

    creation_date = models.DateField(
        blank=False, null=False, default=datetime.date.today,
        verbose_name="Creation date")

    hgvs_string = models.TextField(
        blank=False, null=True, default=None, validators=[valid_hgvs_string])

    scoreset = models.ForeignKey(
        to=ScoreSet, on_delete=models.PROTECT, null=False, default=None)

    # ---------------------------------------------------------------------- #
    #                      Optional Model fields
    # ---------------------------------------------------------------------- #
    data = JSONField(
        verbose_name="Data columns", default=dict({
            SCORES_KEY: {},
            COUNTS_KEY: {}
        }),
        validators=[valid_json_field]
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
        if self.scoreset is None:
            raise IntegrityError("Cannot save when scoreset is None")
        super(Variant, self).save(*args, **kwargs)
        if self.accession is not None:
            valid_var_accession(self.accession)
        else:
            parent = self.scoreset
            parent.validate_variant_data(self)
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
