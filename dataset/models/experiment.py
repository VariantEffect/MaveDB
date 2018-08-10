import string
from functools import reduce

from django.shortcuts import reverse
from django.db import models, transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from accounts.permissions import (
    PermissionTypes,
    create_all_groups_for_instance,
    delete_all_groups_for_instance,
)

from core.utilities import base_url

from genome.models import TargetGene

from urn.models import UrnModel
from urn.validators import validate_mavedb_urn_experiment

from ..models.base import DatasetModel
from ..models.experimentset import ExperimentSet


@transaction.atomic
def assign_public_urn(experiment):
    """
    Assigns a public urn of the form <parent_urn>-[a-z]+ Blocks until it can
    place of lock the passed experiment and experimentset parent. Assumes that
    the parent is already public with a public urn.

    Does nothing if passed model is already public.

    Parameters
    ----------
    experiment : `Experiment`
        The experiment instance to assign a public urn to.
        
    Raises
    ------
    `AttributeError` : Parent does not have a public urn.

    Returns
    -------
    `Experiment`
        experiment with new urn or same urn if already public.
    """
    experiment = Experiment.objects.filter(
        id=experiment.id
    ).select_for_update(nowait=False).first()
    if not experiment.has_public_urn:
        parent = ExperimentSet.objects.filter(
            id=experiment.experimentset.id
        ).select_for_update(nowait=False).first()
        
        if not parent.has_public_urn:
            raise AttributeError(
                "Cannot assign a public urn when parent has a temporary urn."
            )
        
        # Convert child_value to a letter (a-z)
        child_value = parent.last_child_value + 1
        suffix = ""
        x = child_value
        while x > 0:
            x, y = divmod(x - 1, len(string.ascii_lowercase))
            suffix = "{}{}".format(string.ascii_lowercase[y], suffix)
        experiment.urn = "{}-{}".format(parent.urn, suffix)
        parent.last_child_value = child_value
        
        experiment.save()
        parent.save()
        
        # Refresh the instance and nested parents
        experiment = Experiment.objects.filter(
            id=experiment.id
        ).select_for_update(nowait=False).first()
    
    return experiment


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
    #                       Methods
    # ---------------------------------------------------------------------- #
    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.experimentset is None:
            self.experimentset = ExperimentSet.objects.create()
        return super().save(*args, **kwargs)
    
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
    
    def get_url(self, request=None):
        base = base_url(request)
        return base + reverse("dataset:experiment_detail", args=(self.urn,))


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