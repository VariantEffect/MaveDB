import datetime

from django.db import models

from .utilities import format_delta


class TimeStampedModel(models.Model):
    """
    Base model representing a time stamped model updating the modification
    date everytime a change is saved.
    """
    class Meta:
        abstract = True
        ordering = ['-creation_date']

    creation_date = models.DateField(
        default=datetime.date.today,
        verbose_name='Creation date'
    )
    modification_date = models.DateField(
        auto_now=True,  # Automatically set the field to now every save
        verbose_name='Modification date'
    )

    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)

    def format_last_edit_date(self):
        return format_delta(self.modification_date)
