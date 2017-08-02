
import logging
import datetime
import pypandoc
from string import ascii_uppercase

from django.dispatch import receiver
from django.core.exceptions import ValidationError

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save

from .validators import valid_exp_accession, valid_expset_accession
from .validators import valid_wildtype_sequence

logger = logging.getLogger("django")

pdoc_args = [
    '--mathjax',
    '--smart',
    '--standalone',
    '--biblatex',
    '--html-q-tags'
]


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
    # ---------------------------------------------------------------------- #
    #                       Class members/functions
    # ---------------------------------------------------------------------- #
    ACCESSION_DIGITS = 6
    ACCESSION_PREFIX = "EXPS"

    @classmethod
    def build_accession(cls) -> str:
        """
        Creates a new accession by creating a digit that is the count of
        current class (active and inactive) plus 1.

        Parameters
        ----------
        cls : :py:class:`models.base.ModelBase`
            A class that subclasses django's base model.

        Returns
        -------
        `str`:
            The next accession incremented according to the current
            database entries.
        """
        digit_suffix = 1
        if cls.objects.count() > 0:
            accessions = sorted([es.accession for es in cls.objects.all()])
            digit_suffix = int(accessions[-1][len(cls.ACCESSION_PREFIX):]) + 1

        fill_width = cls.ACCESSION_DIGITS - len(str(digit_suffix)) + 1
        accession = cls.ACCESSION_PREFIX + \
            str(digit_suffix).zfill(fill_width)
        return accession

    # ---------------------------------------------------------------------- #
    #                       Model fields
    # ---------------------------------------------------------------------- #
    accession = models.CharField(
        unique=True, default=None, blank=False, null=False,
        max_length=ACCESSION_DIGITS + len(ACCESSION_PREFIX),
        verbose_name="Accession", validators=[valid_expset_accession])

    creation_date = models.DateField(
        blank=False, null=False, default=datetime.date.today, 
        verbose_name="Creation date")

    approved = models.BooleanField(
        blank=False, null=False, default=False, verbose_name="Approved")

    private = models.BooleanField(
        blank=False, null=False, default=True, verbose_name="Private")

    # ---------------------------------------------------------------------- #
    #                       Meta class
    # ---------------------------------------------------------------------- #
    class Meta:
        ordering = ['-creation_date']
        verbose_name = "ExperimentSet"
        verbose_name_plural = "ExperimentSets"

    # ---------------------------------------------------------------------- #
    #                       Data model
    # ---------------------------------------------------------------------- #
    def __str__(self):
        return "ExperimentSet({}, {}, {})".format(
            str(self.accession),
            str(self.creation_date),
            str([e.accession for e in self.experiment_set.all()]))


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

    @classmethod
    def build_accession(cls, parent: ExperimentSet) -> str:
        """
        Creates a new accession by creating a digit that is the count of
        current class (active and inactive) plus 1.

        Parameters
        ----------
        cls : :py:class:`ExperimentSet`
            A class that subclasses django's base model.

        Returns
        -------
        `str`:
            The next accession incremented according to the current
            database entries.
        """
        if not isinstance(parent, ExperimentSet):
            raise TypeError("Parent must be an ExperimentSet instance.")
        try:
            n_existing_experiments = parent.experiment_set.count()
            suffix = ascii_uppercase[n_existing_experiments]
        except IndexError:
            index = n_existing_experiments % len(ascii_uppercase)
            repeat = abs(len(ascii_uppercase) - n_existing_experiments)
            suffix = ascii_uppercase[index] * repeat

        digits = parent.accession[len(ExperimentSet.ACCESSION_PREFIX):]
        accession = '{}{}{}'.format(cls.ACCESSION_PREFIX, digits, suffix)
        return accession

    # ---------------------------------------------------------------------- #
    #                       Required Model fields
    # ---------------------------------------------------------------------- #
    accession = models.CharField(
        unique=True, default=None, blank=False, null=False, max_length=64,
        verbose_name="Accession", validators=[valid_exp_accession])

    creation_date = models.DateField(
        blank=False, null=False, default=datetime.date.today,
        verbose_name="Creation date")

    approved = models.BooleanField(
        blank=False, null=False, default=False, verbose_name="Approved")

    private = models.BooleanField(
        blank=False, null=False, default=True, verbose_name="Private")

    experimentset = models.ForeignKey(
        to=ExperimentSet, on_delete=models.PROTECT, null=False, default=None)

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

    # TODO add the following many2many fields:
    # keywords
    # target organism
    # external accessions
    # reference mapping

    # ---------------------------------------------------------------------- #
    #                       Meta class
    # ---------------------------------------------------------------------- #
    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Experiment"
        verbose_name_plural = "Experiments"

    # ---------------------------------------------------------------------- #
    #                       Data model
    # ---------------------------------------------------------------------- #
    def __str__(self):
        return "Experiment({}, {}, {})".format(
            str(self.accession),
            str(self.experimentset),
            str(self.creation_date))

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    # TODO: add helper functions to check permision bit and author bits
    def md_abstract(self):
        return pypandoc.convert_text(
            self.abstract, 'html', format='md', extra_args=pdoc_args)

    def md_method_desc(self):
        return pypandoc.convert_text(
            self.method_desc, 'html', format='md', extra_args=pdoc_args)
