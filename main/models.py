
import datetime

from django.db import models
from django.core.validators import MinValueValidator

from .utils.pandoc import convert_md_to_html
from experiment.models import Experiment
from scoreset.models import ScoreSet


class News(models.Model):
    # ----------------------------------------------------------------------- #
    #                           Fields
    # ----------------------------------------------------------------------- #
    text = models.TextField(default="default news.", blank=False)
    date = models.DateField(blank=False, default=datetime.date.today)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = "News items"
        verbose_name = "News item"

    def __str__(self):
        return '[{}]: {}'.format(str(self.date), self.text)

    # ----------------------------------------------------------------------- #
    #                           Static
    # ----------------------------------------------------------------------- #
    @staticmethod
    def recent_news():
        return News.objects.all()[0: 10]

    # ----------------------------------------------------------------------- #
    #                           Properties
    # ----------------------------------------------------------------------- #
    @property
    def message(self):
        return str(self)

    # ----------------------------------------------------------------------- #
    #                        Model Validation
    # ----------------------------------------------------------------------- #
    def save(self, *args, **kwargs):
        if self.text is None:
            raise ValueError("A null message is not allowed.")
        elif not self.text.strip():
            raise ValueError("A blank message is not allowed.")

        if self.date is None:
            raise ValueError("A null date is not allowed.")
        try:
            datetime.datetime.strptime(str(self.date), '%Y-%m-%d')
        except ValueError:
            raise ValueError("Incorrect data format, should be YYYY-MM-DD")
        else:
            super().save(*args, **kwargs)


class SiteInformation(models.Model):
    # ----------------------------------------------------------------------- #
    #                           Fields
    # ----------------------------------------------------------------------- #
    _about = models.TextField(default="", blank=True)
    _citation = models.TextField(default="", blank=True)
    _usage_guide = models.TextField(default="", blank=True)
    _documentation = models.TextField(default="", blank=True)
    _terms = models.TextField(default="", blank=True)
    _privacy = models.TextField(default="", blank=True)

    class Meta:
        verbose_name_plural = "Site Information"
        verbose_name = "Site Information"

    # ----------------------------------------------------------------------- #
    #                           Static
    # ----------------------------------------------------------------------- #
    @staticmethod
    def get_instance():
        try:
            return SiteInformation.objects.all()[0]
        except IndexError:
            return SiteInformation()

    # ----------------------------------------------------------------------- #
    #                           Properties
    # ----------------------------------------------------------------------- #
    @property
    def about(self):
        return convert_md_to_html(self._about)

    @property
    def citation(self):
        return convert_md_to_html(self._citation)

    @property
    def usage_guide(self):
        return convert_md_to_html(self._usage_guide)

    @property
    def documentation(self):
        return convert_md_to_html(self._documentation)

    @property
    def terms(self):
        return convert_md_to_html(self._terms)

    @property
    def privacy(self):
        return convert_md_to_html(self._privacy)

    # ----------------------------------------------------------------------- #
    #                        Model Validation
    # ----------------------------------------------------------------------- #
    def can_save(self):
        existing = SiteInformation.objects.all()
        if len(existing) < 1:
            return True
        else:
            return existing[0].pk == self.pk

    def save(self, *args, **kwargs):
        if self._about is None:
            raise ValueError("A null 'about' is not allowed.")
        if self._citation is None:
            raise ValueError("A null 'citation' is not allowed.")
        if self._usage_guide is None:
            raise ValueError("A null 'usage_guide' is not allowed.")
        if self._documentation is None:
            raise ValueError("A null 'documentation' is not allowed.")
        if self._terms is None:
            raise ValueError("A null 'terms' is not allowed.")
        if self._privacy is None:
            raise ValueError("A null 'privacy' is not allowed.")
        if not self.can_save():
            raise ValueError("This is a singleton table. Cannot add entry.")
        else:
            super().save(*args, **kwargs)


class Keyword(models.Model):
    """
    This class represents a keyword that can be associated with an
    experiment or scoreset.
    """
    name = models.TextField(blank=False, null=False, default=None)
    creation_date = models.DateField(blank=False, default=datetime.date.today)
    experiment = models.ForeignKey(
        Experiment, null=True, default=None, on_delete=models.CASCADE)
    scoreset = models.ForeignKey(
        ScoreSet, null=True, default=None, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Keyword"
        verbose_name_plural = "Keywords"

    def __str__(self):
        return "Keyword({})".format(self.name)


class ExternalAccession(models.Model):
    """
    This class represents a textual representation of an accession from an
    external databse that can be associated with a target in an experiment.
    """
    creation_date = models.DateField(blank=False, default=datetime.date.today)
    name = models.TextField(blank=False, null=False, default=None)

    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Other accession"
        verbose_name_plural = "other accessions"

    def __str__(self):
        return "ExternalAccession({})".format(self.name)


class TargetOrganism(models.Model):
    """
    This class represents a textual representation of a target organism
    that can be associated with an experiment.
    """
    creation_date = models.DateField(blank=False, default=datetime.date.today)
    name = models.TextField(blank=False, null=False, default=None)

    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Target organism"
        verbose_name_plural = "Target organisms"

    def __str__(self):
        return "TargetOrganism({})".format(self.name)


class ReferenceMapping(models.Model):
    """
    This class models represents a mapping from local genomic ranges
    within the given target wild type sequence to a genomic range in a 
    reference serquence.
    """
    creation_date = models.DateField(
        blank=False, default=datetime.date.today)
    reference = models.TextField(
        blank=False, null=False, default=None, verbose_name="Reference")
    is_alternate = models.BooleanField(
        blank=False, null=False, default=False,
        verbose_name="Alternate reference")
    experiment = models.OneToOneField(
        Experiment, null=False, default=None, on_delete=models.CASCADE)
    target_start = models.PositiveIntegerField(
        blank=False, null=False, default=None, verbose_name="Target start")
    target_end = models.PositiveIntegerField(
        blank=False, null=False, default=None, verbose_name="Target end")
    ref_start = models.PositiveIntegerField(
        blank=False, null=False, default=None, verbose_name="Reference start")
    ref_end = models.PositiveIntegerField(
        blank=False, null=False, default=None, verbose_name="Reference end")

    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Reference mapping"
        verbose_name_plural = "Reference mappings"

    def __str__(self):
        return "ReferenceMapping({}, {}->{}, {}->{}, {}, {})".format(
            self.name,
            self.target_start, self.target_end,
            self.ref_start, self.ref_end,
            self.is_alternate,
            self.experiment
        )
