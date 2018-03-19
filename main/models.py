import logging
import datetime
import os.path

from django.conf import settings
from django.db import models
from django.db.models import ObjectDoesNotExist

from .utils.pandoc import convert_md_to_html


logger = logging.getLogger("django")


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

    # not currently used
    # additional validation to make sure link is valid?
    @classmethod
    def create_licence(cls, short_name, long_name, file_name, link, version):
        try:
            legal_code = open(
                os.path.join(settings.LICENCE_DIR,
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
                    os.path.join(settings.LICENCE_DIR,
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
                    os.path.join(settings.LICENCE_DIR,
                                 "CC_BY-NC-SA_4.0.txt"),
                    mode='rt'
                ).read(),
                link="https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode",
                version="4.0",
            )
        return licence
