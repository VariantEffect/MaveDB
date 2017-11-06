import datetime

from django.conf import settings
from django.db import models
from django.db.models import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

from .utils.pandoc import convert_md_to_html


class News(models.Model):
    """
    The news model represents an singular piece of news presented in a
    site announcement fashion. News items are sorted by creation date.

    Parameters
    ----------
    text : `models.TextField`
        The content of the news item.abs
    data : `models.DateField`
        The date of creation in yyyy-mm-dd format.
    """
    text = models.TextField(default="default news.", blank=False)
    date = models.DateField(blank=False, default=datetime.date.today)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = "News items"
        verbose_name = "News item"

    def __str__(self):
        return '[{}]: {}'.format(str(self.date), self.text)

    @staticmethod
    def recent_news():
        """
        Return the 10 most recently published news items.
        """
        return News.objects.order_by("-date")[0: 10]

    @property
    def message(self):
        """
        Property for obtaining the text of a news item instance.
        """
        return str(self)

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
    """
    SiteInformation contains all static content of the webapp such as the
    about, citation, documentation etc. This may be replaced with flatpages
    later on in development. There should only be one instance active at any
    time in the database.

    Parameters
    ----------
    _about : `models.TextField`
        The `about` markdown text.
    _citation : `models.TextField`
        The citation for researches to use.
    _usage_guide : `models.TextField`
        A basic guide on how to use the website and api.
    _documentation : `models.TextField`
        API documentation
    _terms : `models.TextField`
        The terms and conditions text blob.
    _privacy : `models.TextField`
        The privacy text blob.
    """
    _about = models.TextField(default="", blank=True)
    _citation = models.TextField(default="", blank=True)
    _usage_guide = models.TextField(default="", blank=True)
    _documentation = models.TextField(default="", blank=True)
    _terms = models.TextField(default="", blank=True)
    _privacy = models.TextField(default="", blank=True)
    _email = models.EmailField(default="", blank=True)

    class Meta:
        verbose_name_plural = "Site Information"
        verbose_name = "Site Information"

    @staticmethod
    def get_instance():
        """
        Tries to get the current instance. If it does not exist, a new one 
        is created.
        """
        try:
            return SiteInformation.objects.all()[0]
        except IndexError:
            return SiteInformation()

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

    @property
    def email(self):
        return self._email

    def can_save(self):
        """
        Checks to see if the current instance can be saved. It will
        return `True` if the instance primary key matches that in the 
        database, or if no `SiteInformation` instances have yet been created.

        Returns
        -------
        `bool`
        """
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

    Parameters
    ----------
    creation_date : `models.DateField`
        The date of instantiation.
    text : `models.TextField`
        The free-form textual representation of the keyword.
    """
    creation_date = models.DateField(blank=False, default=datetime.date.today)
    text = models.CharField(
        blank=False, null=False, default=None, unique=True, max_length=256,
        verbose_name="Keyword"
    )

    @staticmethod
    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Keyword"
        verbose_name_plural = "Keywords"

    def __str__(self):
        return self.text


class ExternalAccession(models.Model):
    """
    This class represents a textual representation of an accession from an
    external databse that can be associated with a target in an experiment.

    Parameters
    ----------
    creation_date : `models.DateField`
        The date of instantiation.
    text : `models.TextField`
        The free-form textual representation of the accession from another
        database.
    """
    creation_date = models.DateField(blank=False, default=datetime.date.today)
    text = models.CharField(
        blank=False, null=False, default=None, unique=True, max_length=256,
        verbose_name="Accession"
    )

    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Other accession"
        verbose_name_plural = "other accessions"

    def __str__(self):
        return self.text


class TargetOrganism(models.Model):
    """
    This class represents a textual representation of a target organism
    that can be associated with an experiment.

    Parameters
    ----------
    creation_date : `models.DateField`
        The date of instantiation.
    text : `models.TextField`
        The free-form textual representation of the target organism.
    """
    creation_date = models.DateField(blank=False, default=datetime.date.today)
    text = models.CharField(
        blank=False, null=False, default=None, unique=True, max_length=256,
        verbose_name="Target Organism"
    )

    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Target organism"
        verbose_name_plural = "Target organisms"

    def __str__(self):
        return self.text


class ReferenceMapping(models.Model):
    """
    This class models represents a mapping from local genomic ranges
    within the given target wild type sequence to a genomic range in a 
    reference serquence.

    Parameters
    ----------
    creation_date : `models.DateField`
        The date of instantiation.
    reference : `models.TextField`
        A string name of the reference being mapped to. There are no
        restrictions on this field except for not being falsey.
    is_alternate : `models.BooleanField`
        Whether this mapping maps to an organism different from the target
        organism of an experiment.
    experiment : `models.ForeignKey`
        The experiment instance this mapping is linked to. This models will
        be deleted if the experiment is also deleted.
    target_start : `models.PositiveIntegerField`
        The starting position within the experiment's target.
    target_end : `models.PositiveIntegerField`
        The ending position within the experiment's target.
    reference_start : `models.PositiveIntegerField`
        The starting position within the reference.
    reference_end : `models.PositiveIntegerField`
        The ending position within the reference.
    """
    creation_date = models.DateField(
        blank=False, default=datetime.date.today)
    reference = models.CharField(
        blank=False, null=False, default=None, unique=False, max_length=256,
        verbose_name="Reference"
    )
    is_alternate = models.BooleanField(
        blank=False, null=False, default=False,
        verbose_name="Alternate reference")
    experiment = models.ForeignKey(
        'experiment.Experiment', null=True, default=None,
        on_delete=models.CASCADE, verbose_name="Experiment target mapping"
    )
    target_start = models.PositiveIntegerField(
        blank=False, null=False, default=None, verbose_name="Target start")
    target_end = models.PositiveIntegerField(
        blank=False, null=False, default=None, verbose_name="Target end")
    reference_start = models.PositiveIntegerField(
        blank=False, null=False, default=None, verbose_name="Reference start")
    reference_end = models.PositiveIntegerField(
        blank=False, null=False, default=None, verbose_name="Reference end")

    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Reference mapping"
        verbose_name_plural = "Reference mappings"

    def __str__(self):
        return "{}, {}->{}, {}->{}, {}".format(
            self.reference,
            self.target_start, self.target_end,
            self.reference_start, self.reference_end,
            self.is_alternate,
        )

    @property
    def datahash(self):
        """
        Build a hash value for this instance intended to check equality
        between two instances. Also achievable through operator overloading,
        but this might affect django's internals.

        Returns
        -------
        `int`
            The hash of the string representation of this instance.
        """
        return hash(str(self))

    def to_json(self):
        return {
            'reference': self.reference,
            'target_start': self.target_start,
            'target_end': self.target_end,
            'reference_start': self.reference_start,
            'reference_end': self.reference_end,
            'is_alternate': self.is_alternate,
        }


class Licence(models.Model):
    """
    This class models represents the licence associated with a
    scoreset.

    Parameters
    ----------
    long_name : `models.CharField`
        The long name of the licence.
    short_name : `models.CharField`
        The short name of the licence.
    text : `models.TextField`
        The actual blob licence text.
    link : `models.CharField`
        The link to the licence.
    version : `models.FloatField`
        Version number of the licence.
    """
    long_name = models.CharField(
        null=False, default=None, verbose_name="Long name", max_length=2048
    )
    short_name = models.CharField(
        null=False, default=None, verbose_name="Short name", max_length=2048
    )
    legal_code = models.TextField(
        verbose_name="Legal Code", null=False, default=None
    )
    link = models.CharField(
        null=False, default=None, verbose_name="Link", max_length=2048
    )
    version = models.FloatField(
        null=False, default=None, verbose_name="Version"
    )

    class Meta:
        verbose_name = "Licence"
        verbose_name_plural = "Licence"

    def __str__(self):
        return self.long_name

    def get_license_legalcode(self):
        return self.legal_code

    @classmethod
    def populate(cls):
        cls.get_cc0()
        cls.get_cc4()

    @classmethod
    def get_default(cls):
        return cls.get_cc4()

    @classmethod
    def get_cc0(cls):
        try:
            licence = cls.objects.get(short_name="CC0")
        except ObjectDoesNotExist:
            licence = cls.objects.create(
                short_name="CC0",
                long_name="CC0 (Public domain)",
                legal_code=open(settings.LICENCE_DIR + "CC0.txt", 'rt').read(),
                link="https://creativecommons.org/publicdomain/zero/1.0/legalcode",
                version=1.0
            )
        return licence

    @classmethod
    def get_cc4(cls):
        try:
            licence = cls.objects.get(short_name="CC BY-NC-SA 4.0")
        except ObjectDoesNotExist:
            licence = cls.objects.create(
                short_name="CC BY-NC-SA 4.0",
                long_name="CC BY-NC-SA 4.0 (Attribution-NonCommercial-ShareAlike)",
                legal_code=open(
                    settings.LICENCE_DIR + "CC_BY-NC-SA_4.0.txt", 'rt'
                ).read(),
                link="https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode",
                version=4.0
            )
        return licence
