from django.db import models, transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from accounts.permissions import (
    PermissionTypes,
    create_all_groups_for_instance,
    delete_all_groups_for_instance,
)

from urn.models import UrnModel
from urn.validators import MAVEDB_URN_NAMESPACE, validate_mavedb_urn_experimentset

from ..models.base import DatasetModel, PublicDatasetCounter


class ExperimentSet(DatasetModel):
    """
    This is the class representing a set of related Experiments. Related
    experiments are those that generally had the same data collection
    methodology, same target, target organism etc, but differed in
    the experimental condition and scoring process.
    """

    class Meta:
        verbose_name = "ExperimentSet"
        verbose_name_plural = "ExperimentSets"
        permissions = (
            (PermissionTypes.CAN_VIEW, "Can view"),
            (PermissionTypes.CAN_EDIT, "Can edit"),
            (PermissionTypes.CAN_MANAGE, "Can manage")
        )

    # ---------------------------------------------------------------------- #
    #                       Model fields
    # ---------------------------------------------------------------------- #
    urn = models.CharField(
        validators=[validate_mavedb_urn_experimentset],
        **UrnModel.default_urn_kwargs
    )

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    def create_urn(self):
        if self.private:
            urn = self.create_temp_urn()
        else:
            counter = PublicDatasetCounter.load()
            
            expset_number = counter.experimentsets + 1
            padded_expset_number = str(expset_number).zfill(self.URN_DIGITS)
            urn = "{}{}".format(self.URN_PREFIX, padded_expset_number)
            
            counter.experimentsets += 1
            counter.save()
        return urn

    def public_experiments(self):
        return self.children.exclude(private=True)

# --------------------------------------------------------------------------- #
#                            Post Save
# --------------------------------------------------------------------------- #
@receiver(post_save, sender=ExperimentSet)
def create_groups_for_experimentset(sender, instance, **kwargs):
    create_all_groups_for_instance(instance)


# --------------------------------------------------------------------------- #
#                            Post Delete
# --------------------------------------------------------------------------- #
@receiver(pre_delete, sender=ExperimentSet)
def delete_groups_for_experimentset(sender, instance, **kwargs):
    delete_all_groups_for_instance(instance)
