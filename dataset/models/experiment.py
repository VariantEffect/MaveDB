import string
import reversion

from django.db import models, transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from accounts.permissions import (
    PermissionTypes,
    create_all_groups_for_instance,
    delete_all_groups_for_instance
)

from genome.models import TargetOrganism
from genome.validators import validate_wildtype_sequence

from urn.models import UrnModel
from urn.validators import validate_mavedb_urn_experiment

from ..models.base import DatasetModel
from ..models.experimentset import ExperimentSet


@reversion.register()
class Experiment(DatasetModel):
    """
    This is the class representing an Experiment. The experiment object
    houses all information relating to a particular experiment up to the
    scoring of its associated variants. This class assumes that all validation
    was handled at the form level, and as such performs no additonal
    validation and will raise IntegreityError if there's bad input.

    Parameters
    ----------
    experimentset : `models.ForeignKey`.
        The experimentset is instance assciated with. New `ExperimentSet` is
        created if this is not provided.

    target : `models.CharField`
        The gene target this experiment examines.

    wt_sequence : `models.CharField`
        The wild type DNA sequence that is related to the `target`. Will
        be converted to upper-case upon instantiation.

    target_organism : `models.ManyToManyField`
        The `TargetOrganism` instance that the target comes from. There should
        only be one associated per `Experiment` instance.
    """
    # ---------------------------------------------------------------------- #
    #                       Class members/functions
    # ---------------------------------------------------------------------- #
    # TODO: Update TRACKED_FIELDS in all classes to use inheritance
    TRACKED_FIELDS = (
        "private",
        "approved",
        "abstract_text",
        "method_text",
        "keywords",
        "pmid_ids",
        "doi_ids",
        "sra_ids",
        "target_organism"
    )

    class Meta:
        verbose_name = "Experiment"
        verbose_name_plural = "Experiments"
        permissions = (
            (PermissionTypes.CAN_VIEW, "Can view"),
            (PermissionTypes.CAN_EDIT, "Can edit"),
            (PermissionTypes.CAN_MANAGE, "Can manage")
        )

    # ---------------------------------------------------------------------- #
    #                       Required Model fields
    # ---------------------------------------------------------------------- #
    urn = models.CharField(
        validators=[validate_mavedb_urn_experiment],
        **UrnModel.default_urn_kwargs
    )

    experimentset = models.ForeignKey(
        to=ExperimentSet,
        on_delete=models.PROTECT,
        null=True,
        default=None,
        blank=True,
        related_name='experiments',
        verbose_name="Experiment Set"
    )

    wt_sequence = models.TextField(
        default=None,
        blank=False,
        null=False,
        verbose_name="Wild type sequence",
        validators=[validate_wildtype_sequence],
    )

    target = models.CharField(
        default=None,
        blank=False,
        null=False,
        verbose_name="Target Gene",
        max_length=256,
    )

    # ---------------------------------------------------------------------- #
    #                       Optional Model fields
    # ---------------------------------------------------------------------- #
    target_organism = models.ManyToManyField(TargetOrganism, blank=True)

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    @transaction.atomic
    def save(self, *args, **kwargs):
        self.wt_sequence = self.wt_sequence.upper()
        if self.experimentset is None:
            self.experimentset = ExperimentSet.objects.create()
        super().save(*args, **kwargs)

    def create_urn(self):
        parent = self.experimentset
        child_value = parent.last_child_value + 1

        # convert child_value to letters
        suffix = ""
        x = child_value
        while x > 0:
            x, y = divmod(x - 1, len(string.ascii_lowercase))
            suffix = "{}{}".format(string.ascii_lowercase[y], suffix)

        urn = "{}-{}".format(parent.urn, suffix)

        # update parent
        parent.last_child_value = child_value
        parent.save()

        return urn

    def update_target_organism(self, target_organism):
        if not isinstance(target_organism, TargetOrganism):
            raise TypeError(
                "`target_organism` must be a TargetOrganism instnace.")
        current = self.target_organism.first()
        if current != target_organism:
            self.target_organism.remove(current)
            self.target_organism.add(target_organism)

    def get_target_organism_name(self):
        if self.target_organism.count():
            return self.target_organism.first().text
        else:
            return None

    def get_wt_sequence(self):
        return self.wt_sequence

    def get_target_name(self):
        return self.target


# --------------------------------------------------------------------------- #
#                               Post Save
# --------------------------------------------------------------------------- #
@receiver(post_save, sender=Experiment)
def create_groups_for_experiment(sender, instance, **kwargs):
    create_all_groups_for_instance(instance)


# --------------------------------------------------------------------------- #
#                            Post Delete
# --------------------------------------------------------------------------- #
@receiver(pre_delete, sender=Experiment)
def delete_groups_for_experiment(sender, instance, **kwargs):
    delete_all_groups_for_instance(instance)