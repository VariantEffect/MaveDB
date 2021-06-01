from django.db import models, transaction
from django.db.models import Count, Sum, F, IntegerField
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
        **UrnModel.default_urn_kwargs,
    )

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    # todo: add tests for below methods
    @classmethod
    def meta_analyses(cls, queryset=None):
        if queryset is None:
            queryset = cls.objects

        field_name = "experiments__scoresets__meta_analysis_for__count"
        o = queryset.annotate(
            **{field_name: Count("experiments__scoresets__meta_analysis_for")}
        )
        return queryset.filter(pk__in=o.filter(**{f"{field_name}__gt": 0}))

    @classmethod
    def non_meta_analyses(cls, queryset=None):
        if queryset is None:
            queryset = cls.objects

        return queryset.exclude(pk__in=cls.meta_analyses(queryset))

    @property
    def children(self):
        return self.experiments.all()

    @property
    def meta_analysis_scoresets(self):
        from .scoreset import ScoreSet

        return ScoreSet.meta_analyses().filter(
            experiment__in=self.experiments.all()
        )

    @property
    def is_meta_analysis(self):
        from .experiment import Experiment

        return (
            0
            < Experiment.meta_analyses().filter(experimentset=self).count()
            == self.children.count()
        )

    @property
    def is_mixed_meta_analysis(self):
        from .scoreset import ScoreSet

        scoreset_count = ScoreSet.objects.filter(
            experiment__in=self.children.all()
        ).count()
        return self.meta_analysis_scoresets.count() > 0 and (
            0 < scoreset_count != self.meta_analysis_scoresets.count()
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
