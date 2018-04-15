from collections import OrderedDict

from django.db import models, transaction
from django.contrib.postgres.fields import JSONField

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
        **UrnModel.default_urn_kwargs
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
    @transaction.atomic
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    @classmethod
    @transaction.atomic
    def bulk_create(cls, parent, variant_kwargs_list, batch_size=None):
        num_variants = len(list(variant_kwargs_list))
        variant_urns = Variant.bulk_create_urns(num_variants, parent)
        variants = (
            Variant(urn=urn, scoreset=parent, **kwargs)
            for urn, kwargs in zip(variant_urns, variant_kwargs_list)
        )
        cls.objects.bulk_create(variants, batch_size=batch_size)
        parent.save()
        return parent.variants.count()

    @staticmethod
    def bulk_create_urns(n, parent):
        start_value = parent.last_child_value
        parent_urn = parent.urn
        child_urns = [
            "{}#{}".format(parent_urn, start_value + (i + 1))
            for i in range(n)
        ]
        parent.last_child_value += n
        return child_urns

    def create_urn(self):
        parent = self.scoreset
        child_value = parent.last_child_value + 1

        urn = "{}#{}".format(parent.urn, child_value)

        # update parent
        parent.last_child_value = child_value
        parent.save()

        return urn

    @property
    def score_columns(self):
        return list(self.data[constants.variant_score_data].keys())

    @property
    def count_columns(self):
        return list(self.data[constants.variant_count_data].keys())

    @property
    def metadata_columns(self):
        return list(self.data[constants.variant_metadata].keys())
