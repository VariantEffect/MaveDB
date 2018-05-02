import logging
import datetime
import os.path

from django.conf import settings
from django.db import models
from django.db.models import ObjectDoesNotExist

from core.models import TimeStampedModel

from core.utilities.pandoc import convert_md_to_html


logger = logging.getLogger("django")


class News(TimeStampedModel):
    """
    The news model represents an singular piece of news presented in a
    site announcement fashion. News items are sorted by creation date.

    Parameters
    ----------
    text : `models.TextField`
        The content of the news item.abs
    """
    STATUS_CHOICES = (
        ('Happy holidays', 'Happy holidays'),
        ('April fools', 'April fools'),
        ('Information', 'Information'),
        ('Important', 'Important'),
        ('Critical', 'Critical'),
    )
    text = models.TextField(default="default news.", blank=False)
    level = models.CharField(
        max_length=250,
        default='Information',
        null=False,
        blank=True,
        choices=STATUS_CHOICES
    )

    class Meta:
        ordering = ['-creation_date']
        verbose_name_plural = "News items"
        verbose_name = "News item"

    def __str__(self):
        return '[{}]: {}'.format(str(self.creation_date), self.text)

    @property
    def date(self):
        return self.creation_date

    @staticmethod
    def recent_news():
        """
        Return the 10 most recently published news items.
        """
        return News.objects.order_by("-creation_date")[0: 10]

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
        return super().save(*args, **kwargs)


class SiteInformation(TimeStampedModel):
    """
    SiteInformation contains all static content of the webapp such as the
    about, citation, documentation etc. This may be replaced with flatpages
    later on in development. There should only be one instance active at any
    time in the database.

    Parameters
    ----------
    about : `TextField`
       The `about` markdown text.
    citation : `TextField`
       The citation for researches to use.
    md_usage_guide : `TextField`
       A basic guide on how to use the website and api.
    documentation : `TextField`
       API documentation
    terms : `TextField`
       The terms and conditions text blob.
    privacy : `TextField`
        The privacy text blob.
    version : `CharField`
        MaveDB release version.
    version_date : `DateTimeField`
        MaveDB version release date.
    """
    about = models.TextField(default="", blank=True)
    citation = models.TextField(default="", blank=True)
    usage_guide = models.TextField(default="", blank=True)
    documentation = models.TextField(default="", blank=True)
    terms = models.TextField(default="", blank=True)
    privacy = models.TextField(default="", blank=True)
    email = models.EmailField(default="", blank=True)
    version = models.CharField(default="1", blank=False, max_length=256)
    version_date = models.DateField(default=datetime.date.today)

    class Meta:
        verbose_name_plural = "Site Information"
        verbose_name = "Site Information"

    @staticmethod
    def get_instance():
        """
        Tries to get the current instance. If it does not exist, a new one 
        is created.
        """
        if SiteInformation.objects.first():
            return SiteInformation.objects.first()
        return SiteInformation()

    def md_about(self):
        return convert_md_to_html(self.about)

    def md_citation(self):
        return convert_md_to_html(self.citation)

    @property
    def md_usage_guide(self):
        return convert_md_to_html(self.usage_guide)

    @property
    def md_documentation(self):
        return convert_md_to_html(self.documentation)

    @property
    def md_terms(self):
        return convert_md_to_html(self.terms)

    @property
    def md_privacy(self):
        return convert_md_to_html(self.privacy)

    @property
    def contact_email(self):
        return self.email

    @property
    def release_version(self):
        return self.version

    @property
    def release_date(self):
        return self.version_date

    def can_save(self):
        """
        Checks to see if the current instance can be saved. It will
        return `True` if the instance primary key matches that in the 
        database, or if no `SiteInformation` instances have yet been created.

        Returns
        -------
        `bool`
        """
        existing = SiteInformation.objects.first()
        if existing is None:
            return True
        return self.pk == existing.pk


class Licence(TimeStampedModel):
    """
    This class models represents the licence associated with a
    scoreset.

    Parameters
    ----------
    long_name : `models.CharField`
        The long name of the licence.
    short_name : `models.CharField`
        The short name of the licence.
    legal_code : `models.TextField`
        The actual blob licence text.
    link : `models.URLField`
        The link to the licence.
    version : `models.CharField`
        Semantic version number of the licence.
    """
    long_name = models.CharField(
        null=False,
        default=None,
        verbose_name="Long name",
        max_length=200,
    )
    short_name = models.CharField(
        null=False,
        default=None,
        verbose_name="Short name",
        max_length=200,
    )
    legal_code = models.TextField(
        verbose_name="Legal Code",
        null=False,
        default=None,
    )
    link = models.URLField(
        null=False,
        default=None,
        verbose_name="Link",
    )
    version = models.CharField(
        null=False,
        default=None,
        verbose_name="Version",
        max_length=200,
    )

    class Meta:
        verbose_name = "Licence"
        verbose_name_plural = "Licence"

    def __str__(self):
        return self.long_name

    def get_legal_code(self):
        return self.legal_code

    def get_long_name(self):
        return self.long_name

    def get_short_name(self):
        return self.short_name

    # not currently used
    # additional validation to make sure link is valid?
    @classmethod
    def create_licence(cls, short_name, long_name, file_name, link, version):
        try:
            legal_code = open(
                os.path.join(settings.MAIN_DIR,
                             file_name),
                mode='rt'
            ).read()
        except IOError as e:
            logging.error("Failed to read licence file for{license} "
                          "('{file}'): {error}".format(license=short_name,
                                                       file=file_name,
                                                       error=e))
            legal_code = "UNDEFINED"
        cls.objects.create(
            short_name=short_name,
            long_name=long_name,
            legal_code=legal_code,
            link=link,
            version=version,
        )

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
                legal_code=open(
                    os.path.join(settings.MAIN_DIR,
                                 "CC0.txt"),
                    mode='rt'
                ).read(),
                link="https://creativecommons.org/publicdomain/zero/1.0/legalcode",
                version="1.0",
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
                    os.path.join(settings.MAIN_DIR,
                                 "CC_BY-NC-SA_4.0.txt"),
                    mode='rt'
                ).read(),
                link="https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode",
                version="4.0",
            )
        return licence
