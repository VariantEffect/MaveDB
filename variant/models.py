from django.contrib.postgres.fields import JSONField
from django.db import models

from dataset import constants as constants
from variant.validators import validate_variant_json
from urn.models import UrnModel
from urn.validators import validate_mavedb_urn_variant

from .validators import validate_hgvs_string


class Variant(UrnModel):
    """
    This is the class representing an individual variant belonging to one
    and only one ScoreSet instance. The numerical parameters of a variant
    are held in a JSONField, which can be easily queried and extended as
    needed.

    Parameters
    ----------
    hgvs : `str`, required.
        The HGVS string belonging to the variant.

    scoreset : `ScoreSet`, required.
        The associated scoreset of the instance.

    data : `JSONField`
        The variant's numerical data.

    """
    # ---------------------------------------------------------------------- #
    #                       Class members/functions
    # ---------------------------------------------------------------------- #
    class Meta:
        verbose_name = "Variant"
        verbose_name_plural = "Variants"

    # ---------------------------------------------------------------------- #
    #                       Required Model fields
    # ---------------------------------------------------------------------- #
    urn = models.CharField(
        validators=[validate_mavedb_urn_variant],
        **UrnModel.default_urn_kwargs,
    )

    hgvs = models.TextField(
        blank=False,
        null=False,
        default=None,
        validators=[validate_hgvs_string],
    )

    scoreset = models.ForeignKey(
        to='dataset.ScoreSet',
        on_delete=models.PROTECT,
        related_name='variants',
        null=False,
        default=None,
    )

    # ---------------------------------------------------------------------- #
    #                      Optional Model fields
    # ---------------------------------------------------------------------- #
    data = JSONField(
        verbose_name="Data columns",
        default=dict({
            constants.variant_score_data: {},
            constants.variant_count_data: {},
            constants.variant_metadata: {}
        }),
        validators=[validate_variant_json],
    )

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    @property
    def score_columns(self):
        return list(self.data[constants.variant_score_data].keys())

    @property
    def count_columns(self):
        return list(self.data[constants.variant_count_data].keys())

    @property
    def metadata_columns(self):
        return list(self.data[constants.variant_metadata].keys())

    def get_ordered_score_data(self):
        columns = self.scoreset.score_columns
        data = [self.data[constants.variant_score_data][key] for key in columns]
        return data

    def get_ordered_count_data(self):
        columns = self.scoreset.count_columns
        data = [self.data[constants.variant_count_data][key] for key in columns]
        return data