import random
import string

from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction

from core.models import TimeStampedModel

from .validators import MAVEDB_EXPERIMENTSET_URN_DIGITS, \
    MAVEDB_URN_MAX_LENGTH, MAVEDB_URN_NAMESPACE, \
    MAVEDB_TMP_URN_DIGITS


RANDOM_CHARS = string.ascii_lowercase + string.ascii_uppercase + string.digits


def get_model_by_urn(urn):
    from variant.models import Variant
    from dataset.models.scoreset import ScoreSet
    from dataset.models.experiment import Experiment
    from dataset.models.experimentset import ExperimentSet

    for model in [ScoreSet, Experiment, ExperimentSet, Variant]:
        if model.objects.filter(urn=urn).exists():
            return model.objects.get(urn=urn)
    raise ObjectDoesNotExist("No model found with urn {}.".format(urn))


def generate_tmp_urn():
    return 'tmp:{}'.format(
        ''.join([
            random.choice(RANDOM_CHARS)
            for _ in range(MAVEDB_TMP_URN_DIGITS)
    ]))


class UrnModel(TimeStampedModel):
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
        return str(self.get_display_urn())

    @transaction.atomic
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.urn is None:
            # This needs access to the PK so the instance must be saved first
            # and then saved again.
            self.urn = self.create_temp_urn()
            self.save()

    @classmethod
    def create_temp_urn(cls):
        urn = generate_tmp_urn()
        while cls.objects.filter(urn=urn).count() > 0:
            urn = generate_tmp_urn()
        return urn
        
    def get_display_urn(self):
        if self.urn:
            return self.urn
        
    @property
    def has_public_urn(self):
        return 'urn:' in str(self.urn)
