import datetime

from django.db import models


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
    modified_date = models.DateField(
        default=datetime.date.today,
        verbose_name='Modification date'
    )

    def save(self, *args, **kwargs):
        self.modified_date = datetime.date.today()
        return super().save(*args, **kwargs)
