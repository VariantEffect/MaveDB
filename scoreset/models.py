import logging
import datetime
import pypandoc

from django.dispatch import receiver
from django.core.exceptions import ValidationError

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save

from .validators import valid_scs_accession
from experiment.models import Experiment

logger = logging.getLogger("django")
pdoc_args = [
    '--mathjax',
    '--smart',
    '--standalone',
    '--biblatex',
    '--html-q-tags'
]


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

    @classmethod
    def build_accession(cls, parent: Experiment) -> str:
        """
        Creates a new accession by creating a digit that is the count of
        current class (active and inactive) plus 1.

        Parameters
        ----------
        cls : :py:class:`Experiment`
            A class that subclasses django's base model.

        Returns
        -------
        `str`:
            The next accession incremented according to the current
            database entries.
        """
        if not isinstance(parent, Experiment):
            raise TypeError("Parent must be an Experiment instance.")
        n_existing_scoresets = parent.scoreset_set.count()
        suffix = '.{}'.format(n_existing_scoresets + 1)
        digits = parent.accession[len(ExperimentSet.ACCESSION_PREFIX):]
        accession = '{}{}{}'.format(cls.ACCESSION_PREFIX, digits, suffix)
        return accession

    # ---------------------------------------------------------------------- #
    #                       Required Model fields
    # ---------------------------------------------------------------------- #
    accession = models.CharField(
        unique=True, default=None, blank=False, null=False, max_length=64,
        verbose_name="Accession", validators=[valid_scs_accession])

    creation_date = models.DateField(
        blank=False, null=False, default=datetime.date.today,
        verbose_name="Creation date")

    approved = models.BooleanField(
        blank=False, null=False, default=False, verbose_name="Approved")

    private = models.BooleanField(
        blank=False, null=False, default=True, verbose_name="Private")

    experiment = models.ForeignKey(
        to=Experiment, on_delete=models.PROTECT, null=False, default=None)

    # TODO add dataset jsonfield

    # ---------------------------------------------------------------------- #
    #                       Optional Model fields
    # ---------------------------------------------------------------------- #
    abstract = models.TextField(
        blank=True, default="", verbose_name="Abstract")
    method_desc = models.TextField(
        blank=True, default="", verbose_name="Method description")
    doi_id = models.TextField(
        blank=True, default="", verbose_name="DOI identifier")

    # TODO add the following many2many fields:
    # keywords
    # metadata

    # ---------------------------------------------------------------------- #
    #                       Meta class
    # ---------------------------------------------------------------------- #
    class Meta:
        ordering = ['-creation_date']
        verbose_name = "ScoreSet"
        verbose_name_plural = "ScoreSets"

    # ---------------------------------------------------------------------- #
    #                       Data model
    # ---------------------------------------------------------------------- #
    def __str__(self):
        return "Experiment({}, {}, {})".format(
            str(self.accession),
            str(self.experiment),
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
