from django.db import models, transaction

# Create your models here.
from .validators import MAVEDB_EXPERIMENTSET_URN_DIGITS, \
    MAVEDB_URN_MAX_LENGTH, MAVEDB_URN_NAMESPACE


class UrnModel(models.Model):
    """
    Abstract class for all entries in MAVEDB that have a URN.

    Parameters
    ----------
    urn : `models.CharField`
        The urn in the MAVEDB URN format:
        `urn:mavedb:<ExperimentSet>-<Experiment>-<ScoreSet>#<Variant>`, where
        `<ExperimentSet>` is a zero-padded eight-digit integer, `<Experiment>`
        is a lowercase letter or string of letters ('aa' follows 'z' in the rare
        case that more than 26 Experiments are associated with a single
        ExperimentSet), `<ScoreSet>` is an integer with no padding, and
        `<Variant>` is an integer with no padding.
    """
    URN_PREFIX = "urn:{}:".format(MAVEDB_URN_NAMESPACE)
    URN_DIGITS = MAVEDB_EXPERIMENTSET_URN_DIGITS

    class Meta:
        abstract = True
        ordering = ['-creation_date']

    default_urn_kwargs = {
        "unique": True,
        "default": None,
        "blank": True,
        "null": True,
        "max_length": MAVEDB_URN_MAX_LENGTH,
        "verbose_name": "URN",
    }

    # ---------------------------------------------------------------------- #
    #                       Model fields
    # ---------------------------------------------------------------------- #
    urn = None

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    def __str__(self):
        return str(self.urn)

    @transaction.atomic
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.urn is None:
            self.urn = self.create_urn()
            self.save()

    def create_urn(self):
        raise NotImplementedError()
