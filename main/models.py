
import datetime

from django.db import models
from django.core.validators import MinValueValidator

import pypandoc
pdoc_args = [
    '--mathjax',
    '--smart',
    '--standalone',
    '--biblatex',
    '--html-q-tags'
]


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
        return pypandoc.convert_text(
            self._about, 'html', format='md', extra_args=pdoc_args)

    @property
    def citation(self):
        return pypandoc.convert_text(
            self._citation, 'html', format='md', extra_args=pdoc_args)

    @property
    def usage_guide(self):
        return pypandoc.convert_text(
            self._usage_guide, 'html', format='md', extra_args=pdoc_args)

    @property
    def documentation(self):
        return pypandoc.convert_text(
            self._documentation, 'html', format='md', extra_args=pdoc_args)

    @property
    def terms(self):
        return pypandoc.convert_text(
            self._terms, 'html', format='md', extra_args=pdoc_args)

    @property
    def privacy(self):
        return pypandoc.convert_text(
            self._privacy, 'html', format='md', extra_args=pdoc_args)

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
