
import datetime
from django.db import models
from markdownx.models import MarkdownxField
from markdownx.utils import markdownify


class News(models.Model):
    text = models.TextField(blank=False, default="")
    date = models.DateField(blank=False, default=datetime.date.today)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = "News items"
        verbose_name = "News item"

    def __str__(self):
        return '[{}]: {}'.format(str(self.date), self.text)

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

    @property
    def message(self):
        return str(self)

    @staticmethod
    def recent_news():
        return News.objects.all()[0: 10]


class SiteInformation(models.Model):
    about = models.TextField(default="", blank=False)
    citation = models.TextField(default="", blank=False)

    class Meta:
        verbose_name_plural = "Site Information"
        verbose_name = "Site Information"

    def can_save(self):
        existing = SiteInformation.objects.all()
        if len(existing) < 1:
            return True
        else:
            return existing[0].pk == self.pk
        
    def save(self, *args, **kwargs):
        if self.about is None:
            raise ValueError("A null about is not allowed.")
        elif not self.about.strip():
            raise ValueError("A blank about is not allowed.")
        if self.citation is None:
            raise ValueError("A null citation is not allowed.")
        elif not self.citation.strip():
            raise ValueError("A blank citation is not allowed.")
        
        if not self.can_save():
            raise ValueError("This is a singleton table. Cannot add entry.")
        else:
            super().save(*args, **kwargs)
