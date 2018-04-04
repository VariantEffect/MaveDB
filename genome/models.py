import datetime

from django.db import models, IntegrityError, transaction


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
    creation_date = models.DateField(
        blank=False,
        default=datetime.date.today
    )
    text = models.CharField(
        blank=False,
        null=False,
        default=None,
        unique=True,
        max_length=256,
        verbose_name="Target Organism",
    )

    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Target organism"
        verbose_name_plural = "Target organisms"

    def __str__(self):
        return self.text


class ReferenceGenome(models.Model):
    pass


class WildTypeSequence(models.Model):
    pass


class TargetGene(models.Model):
    pass
