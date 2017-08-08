
import logging
import datetime
from string import ascii_uppercase

from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

from django.conf import settings
from django.db import models, IntegrityError
from django.db.models.signals import pre_save, post_save

from .validators import valid_exp_accession, valid_expset_accession
from .validators import valid_wildtype_sequence

from main.models import Keyword, ExternalAccession, TargetOrganism

logger = logging.getLogger("django")
positive_integer_validator = MinValueValidator(limit_value=0)


class ExperimentSet(models.Model):
    """
    This is the class representing a set of related Experiments. Related
    experiments are those that generally had the same data collection
    methodology, same target, target organism etc, but differed in
    the experimental condition and scoring process.

    Parameters
    ----------
    accession : `str`
        This is the only required field, and should be specified at all points
        of instantiation (ExperimentSet, ExperimentSet.objects.create).
    Methods
    -------
    build_accession
        Creates a new accession by creating a digit that has the digit bit of
        the last accession when sorted in ascending order plus one.
    """

    ACCESSION_DIGITS = 6
    ACCESSION_PREFIX = "EXPS"

    class Meta:
        ordering = ['-creation_date']
        verbose_name = "ExperimentSet"
        verbose_name_plural = "ExperimentSets"

    # ---------------------------------------------------------------------- #
    #                       Model fields
    # ---------------------------------------------------------------------- #
    accession = models.CharField(
        unique=True, default=None, blank=False, null=True,
        max_length=ACCESSION_DIGITS + len(ACCESSION_PREFIX),
        verbose_name="Accession", validators=[valid_expset_accession])

    last_used_suffix = models.CharField(
        blank=True, null=True, default="", max_length=64)

    creation_date = models.DateField(
        blank=False, null=False, default=datetime.date.today,
        verbose_name="Creation date")

    approved = models.BooleanField(
        blank=False, null=False, default=False, verbose_name="Approved")

    private = models.BooleanField(
        blank=False, null=False, default=True, verbose_name="Private")

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    def __str__(self):
        return "ExperimentSet({}, {}, {})".format(
            str(self.accession),
            str(self.creation_date),
            str([e.accession for e in self.experiment_set.all()]))

    def save(self, *args, **kwargs):
        super(ExperimentSet, self).save(*args, **kwargs)
        if self.accession is not None:
            valid_expset_accession(self.accession)
        else:
            digit_bit = str(self.pk)
            digit_suffix = digit_bit.zfill(self.ACCESSION_DIGITS)
            accession = "{}{}".format(self.ACCESSION_PREFIX, digit_suffix)
            self.accession = accession
            self.save()

    def next_experiment_suffix(self):
        if not self.last_used_suffix:
            suffix = ascii_uppercase[0]
        else:
            last_used = self.last_used_suffix
            index = ascii_uppercase.index(last_used[0].upper()) + 1
            times_to_repeat = len(last_used)
            if index >= len(ascii_uppercase):
                times_to_repeat += 1
            next_index = index % len(ascii_uppercase)
            suffix = ascii_uppercase[next_index] * times_to_repeat
        return suffix


class Experiment(models.Model):
    """
    This is the class representing an Experiment. The experiment object
    houses all information relating to a particular experiment up to the
    scoring of its associated variants. This class assumes that all validation
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
    ACCESSION_PREFIX = "EXP"

    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Experiment"
        verbose_name_plural = "Experiments"

    # ---------------------------------------------------------------------- #
    #                       Required Model fields
    # ---------------------------------------------------------------------- #
    accession = models.CharField(
        unique=True, default=None, null=True, max_length=64,
        verbose_name="Accession", validators=[valid_exp_accession])

    experimentset = models.ForeignKey(
        to=ExperimentSet, on_delete=models.PROTECT, null=True, default=None)

    creation_date = models.DateField(
        blank=False, null=False, default=datetime.date.today,
        verbose_name="Creation date")

    last_used_suffix = models.IntegerField(
        default=0, validators=[positive_integer_validator])

    approved = models.BooleanField(
        blank=False, null=False, default=False, verbose_name="Approved")

    private = models.BooleanField(
        blank=False, null=False, default=True, verbose_name="Private")

    wt_sequence = models.TextField(
        default=None, blank=False, null=False,
        verbose_name="Wild type sequence",
        validators=[valid_wildtype_sequence])

    target = models.TextField(
        default=None, blank=False, null=False, verbose_name="Target")

    # ---------------------------------------------------------------------- #
    #                       Optional Model fields
    # ---------------------------------------------------------------------- #
    abstract = models.TextField(
        blank=True, default="", verbose_name="Abstract")
    method_desc = models.TextField(
        blank=True, default="", verbose_name="Method description")
    sra_id = models.TextField(
        blank=True, default="", verbose_name="SRA identifier")
    doi_id = models.TextField(
        blank=True, default="", verbose_name="DOI identifier")

    keywords = models.ManyToManyField(Keyword)
    external_accessions = models.ManyToManyField(ExternalAccession)
    target_organism = models.ManyToManyField(TargetOrganism)

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    # TODO: add helper functions to check permision bit and author bits
    def __str__(self):
        return "Experiment(id: {}, acc: {}, in set: {}, created: {})".format(
            str(self.pk), str(self.accession),
            str(self.experimentset.accession),
            str(self.creation_date))

    def save(self, *args, **kwargs):
        super(Experiment, self).save(*args, **kwargs)
        if self.accession is not None:
            valid_exp_accession(self.accession)
        else:
            expset = None
            if self.experimentset is None:
                expset = ExperimentSet.objects.create()
                self.experimentset = expset

            parent = self.experimentset
            suffix = parent.next_experiment_suffix()
            accession = "{}{}".format(
                parent.accession.replace(
                    parent.ACCESSION_PREFIX, self.ACCESSION_PREFIX
                ),
                suffix
            )
            parent.last_used_suffix = suffix
            parent.save()
            self.accession = accession
            self.save()

    def next_scoreset_suffix(self):
        return self.last_used_suffix + 1

    def md_abstract(self):
        return pypandoc.convert_text(
            self.abstract, 'html', format='md', extra_args=pdoc_args)

    def md_method_desc(self):
        return pypandoc.convert_text(
            self.method_desc, 'html', format='md', extra_args=pdoc_args)
