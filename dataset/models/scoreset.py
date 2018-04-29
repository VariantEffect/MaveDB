import reversion

from django.contrib.postgres.fields import JSONField
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from accounts.permissions import (
    PermissionTypes,
    create_all_groups_for_instance,
    delete_all_groups_for_instance,
)

from main.models import Licence

from urn.models import UrnModel
from urn.validators import validate_mavedb_urn_scoreset

from dataset import constants as constants
from ..models.base import DatasetModel
from ..models.experiment import Experiment
from ..validators import validate_scoreset_json


User = get_user_model()

def default_dataset():
    return dict({
        constants.score_columns: [constants.required_score_column],
        constants.count_columns: [],
        constants.meta_columns: []
    })


@reversion.register()
class ScoreSet(DatasetModel):
    """
    This is the class representing a set of scores for an experiment.
    The ScoreSet object houses all information relating to a particular
    method of variant scoring. This class assumes that all validation
    was handled at the form level, and as such performs no additonal
    validation and will raise IntegreityError if there's bad input.

    Parameters
    ----------
    urn : `models.CharField`
        The urn in the format 'SCSXXXXXX[A-Z]+.\d+'

    experiment : `models.ForeignKey`, required.
        The experiment a scoreset is assciated with. Cannot be null.

    licence : `models.ForeignKey`
        Licence type attached to the instance.

    target : 'models.ForeignKey`:
        The target gene of the scored variants.

    dataset_columns : `models.JSONField`
        A JSON instances with keys `scores` and `counts`. The values are
        lists of strings indicating the columns to be expected in the variants
        for this dataset.

    replaces : `models.ForeignKey`
        Indicates a scoreset instances that replaces the current instance.
    """
    # ---------------------------------------------------------------------- #
    #                       Class members/functions
    # ---------------------------------------------------------------------- #
    # TODO: Update TRACKED_FIELDS in all classes to use inheritance
    TRACKED_FIELDS = (
        "private", "approved", "abstract_text",
        "method_text", "doi_ids", "sra_ids", "pubmed_ids", "keywords",
        "licence", "dataset_columns", "replaces", "short_description",
        "title",
    )

    class Meta:
        verbose_name = "ScoreSet"
        verbose_name_plural = "ScoreSets"
        permissions = (
            (PermissionTypes.CAN_VIEW, "Can view"),
            (PermissionTypes.CAN_EDIT, "Can edit"),
            (PermissionTypes.CAN_MANAGE, "Can manage")
        )

    # ---------------------------------------------------------------------- #
    #                       Required Model fields
    # ---------------------------------------------------------------------- #
    urn = models.CharField(
        validators=[validate_mavedb_urn_scoreset],
        **UrnModel.default_urn_kwargs
    )

    experiment = models.ForeignKey(
        to=Experiment,
        on_delete=models.PROTECT,
        null=False,
        default=None,
        verbose_name='Experiment',
        related_name='scoresets',
    )

    licence = models.ForeignKey(
        to=Licence, on_delete=models.DO_NOTHING,
        verbose_name="Licence",
        related_name="attached_scoresets",
        default=None,
        null=True,
        blank=True,
    )

    dataset_columns = JSONField(
        verbose_name="Dataset columns",
        default=default_dataset(),
        validators=[validate_scoreset_json],
    )

    replaces = models.OneToOneField(
        to='dataset.ScoreSet',
        on_delete=models.DO_NOTHING,
        null=True,
        verbose_name="Replaces",
        related_name="replaced_by",
        blank=True,
    )

    normalised = models.BooleanField(
        default=False,
        blank=True,
        null=False,
        verbose_name="Scores are normalised",
    )

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.licence is None:
            self.licence = Licence.get_default()
        super().save(*args, **kwargs)

    def create_urn(self):
        parent = self.experiment
        child_value = parent.last_child_value + 1

        urn = "{}-{}".format(parent.urn, child_value)

        # update parent
        parent.last_child_value = child_value
        parent.save()

        return urn

    # Variant related methods
    # ---------------------------------------------------------------------- #
    @property
    def has_variants(self):
        return hasattr(self, 'variants') and self.variants.count() > 0

    @property
    def variant_count(self):
        return self.variants.count()

    def delete_variants(self):
        if self.has_variants:
            self.variants.all().delete()
            self.dataset_columns = default_dataset()
            self.last_child_value = 0
            self.save()

    def get_target(self):
        if not hasattr(self, 'target'):
            return None
        return self.target

    def get_target_organisms(self):
        if not self.get_target():
            return set()
        return set([
            g.get_species_name()
            for g in self.get_target().get_reference_genomes()
        ])

    def get_display_target_organisms(self):
        if not self.get_target():
            return set()
        return set(sorted([
            r.format_reference_genome_species_html()
            for r in self.get_target().get_reference_maps()
        ]))

    # JSON field related methods
    # ---------------------------------------------------------------------- #
    def _add_hgvs(self, ls):
        return [constants.hgvs_column] + ls

    @property
    def score_columns(self):
        return self._add_hgvs(self.dataset_columns[constants.score_columns])

    @property
    def count_columns(self):
        return self._add_hgvs(self.dataset_columns[constants.count_columns])

    @property
    def metadata_columns(self):
        return self._add_hgvs(self.dataset_columns[constants.meta_columns])

    @property
    def has_score_dataset(self):
        return len(self.dataset_columns[constants.score_columns]) > 0

    @property
    def has_count_dataset(self):
        return len(self.dataset_columns[constants.count_columns]) > 0

    @property
    def has_metadata(self):
        return len(self.dataset_columns[constants.meta_columns]) > 0

    # replaced_by/replaces chain traversal
    # ---------------------------------------------------------------------- #
    @property
    def has_replacement(self):
        return hasattr(self, 'replaced_by')

    @property
    def replaces_previous(self):
        return hasattr(self, 'replaces')

    @property
    def current_version(self):
        next_instance = self
        while next_instance.next_version is not None:
            next_instance = next_instance.next_version
        return next_instance

    @property
    def next_version(self):
        if self.has_replacement:
            return self.replaced_by
        return None

    @property
    def previous_version(self):
        if self.replaces_previous:
            return self.replaces
        return None


# --------------------------------------------------------------------------- #
#                               Post Save
# --------------------------------------------------------------------------- #
@receiver(post_save, sender=ScoreSet)
def create_permission_groups_for_scoreset(sender, instance, **kwargs):
    create_all_groups_for_instance(instance)


# --------------------------------------------------------------------------- #
#                            Post Delete
# --------------------------------------------------------------------------- #
@receiver(pre_delete, sender=ScoreSet)
def delete_permission_groups_for_scoreset(sender, instance, **kwargs):
    delete_all_groups_for_instance(instance)