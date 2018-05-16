import string
import reversion
from functools import reduce

from django.db import models, transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from accounts.permissions import (
    PermissionTypes,
    create_all_groups_for_instance,
    delete_all_groups_for_instance,
)

from genome.models import TargetGene

from urn.models import UrnModel
from urn.validators import validate_mavedb_urn_experiment

from ..models.base import DatasetModel, PublicDatasetCounter
from ..models.experimentset import ExperimentSet


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
    """
    # ---------------------------------------------------------------------- #
    #                       Class members/functions
    # ---------------------------------------------------------------------- #
    # TODO: Update TRACKED_FIELDS in all classes to use inheritance

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

    # ---------------------------------------------------------------------- #
    #                       Optional Model fields
    # ---------------------------------------------------------------------- #
    targets = models.ManyToManyField(TargetGene, blank=False)

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.experimentset is None:
            self.experimentset = ExperimentSet.objects.create()
        super().save(*args, **kwargs)
    
    @transaction.atomic
    def create_urn(self):
        if self.private or not self.experimentset.has_public_urn:
            urn = self.create_temp_urn()
        else:
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
            
            # Add new public dataset to counter
            counter = PublicDatasetCounter.load()
            counter.experiments += 1
            counter.save()
    
        return urn

    def get_targets(self):
        target_pks = set([
            child.get_target().pk for child in self.children
            if child.get_target()]
        )
        return TargetGene.objects.filter(pk__in=target_pks)

    def get_target_names(self):
        return list(sorted(set([t.get_name() for t in self.get_targets()])))

    def get_target_organisms(self):
        organism_sets = [
            s.get_target_organisms() for s in self.children]
        return list(
            sorted(set(reduce(lambda x, y: x | y, organism_sets, set()))))

    def get_display_target_organisms(self):
        organism_sets = [
            s.get_display_target_organisms() for s in self.children]
        return list(
            sorted(set(reduce(lambda x, y: x | y, organism_sets, set()))))

    def public_scoresets(self):
        return self.children.exclude(private=True)


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