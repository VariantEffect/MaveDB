from django.db import models, transaction
from django.db.models import Count
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.shortcuts import reverse

from accounts.permissions import (
    PermissionTypes,
    create_all_groups_for_instance,
    delete_all_groups_for_instance,
)

from core.utilities import base_url

from urn.models import UrnModel
from urn.validators import validate_mavedb_urn_experimentset

from ..models.base import DatasetModel, PublicDatasetCounter


@transaction.atomic
def assign_public_urn(experimentset):
    """
    Assigns a public urn of the form urn:mavedb:0000000X. Blocks until it can
    place of lock the passed experimentset and `PublicDatasetCounter` singleton.

    Does nothing if passed model is already public.

    Parameters
    ----------
    experimentset : `ExperimentSet`
        The experimentset instance to assign a public urn to.

    Returns
    -------
    `ExperimentSet`
        experimentset with new urn or same urn if already public.
    """
    experimentset = (
        ExperimentSet.objects.filter(id=experimentset.id)
        .select_for_update(nowait=False)
        .first()
    )
    if not experimentset.has_public_urn:
        counter = (
            PublicDatasetCounter.objects.filter(
                id=PublicDatasetCounter.load().id
            )
            .select_for_update(nowait=False)
            .first()
        )

        expset_number = counter.experimentsets + 1
        padded_expset_number = str(expset_number).zfill(
            ExperimentSet.URN_DIGITS
        )
        urn = "{}{}".format(ExperimentSet.URN_PREFIX, padded_expset_number)

        experimentset.urn = urn
        counter.experimentsets += 1
        experimentset.save()
        counter.save()

        # Refresh the instance.
        experimentset = (
            ExperimentSet.objects.filter(id=experimentset.id)
            .select_for_update(nowait=False)
            .first()
        )

    return experimentset


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
            (PermissionTypes.CAN_MANAGE, "Can manage"),
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
    @classmethod
    def meta_analyses(cls):
        o = cls.objects.annotate(
            experiments__scoresets__meta_analysis_for_count=Count(
                "experiments__scoresets__meta_analysis_for"
            )
        )
        return o.filter(experiments__scoresets__meta_analysis_for_count__gt=0)

    @classmethod
    def non_meta_analyses(cls):
        o = cls.objects.annotate(
            experiments__scoresets__meta_analysis_for_count=Count(
                "experiments__scoresets__meta_analysis_for"
            )
        )
        return o.exclude(experiments__scoresets__meta_analysis_for_count__gt=0)

    @property
    def children(self):
        return self.experiments.all()

    @property
    def is_parent_of_meta_analysis(self):
        from .experiment import Experiment

        return (
            Experiment.meta_analyses()
            .filter(id__in=self.children.all())
            .count()
            > 0
        )

    def public_experiments(self):
        return self.children.exclude(private=True)

    def get_url(self, request=None):
        base = base_url(request)
        return base + reverse("dataset:experimentset_detail", args=(self.urn,))


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
