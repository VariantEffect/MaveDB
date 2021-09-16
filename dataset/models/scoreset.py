from billiard.exceptions import SoftTimeLimitExceeded
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
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
from core.models import FailedTask
from core.utilities import base_url
from dataset import constants as constants
from main.models import Licence
from urn.models import UrnModel
from urn.validators import validate_mavedb_urn_scoreset
from ..models.base import DatasetModel
from ..models.experiment import Experiment
from ..validators import validate_scoreset_json, WordLimitValidator


User = get_user_model()


def default_dataset():
    return dict(
        {
            constants.score_columns: [constants.required_score_column],
            constants.count_columns: [],
        }
    )


@transaction.atomic
def assign_public_urn(scoreset):
    """
    Assigns a public urn of the form <parent_urn>-[0-9]+ Blocks until it can
    place of lock the passed `scoreset` and `experiment` parent. Assumes that
    the parent is already public with a public urn.

    Does nothing if passed model is already public.

    Parameters
    ----------
    scoreset : `ScoreSet`
        The scoreset instance to assign a public urn to.

    Raises
    ------
    `AttributeError` : Parent does not have a public urn.

    Returns
    -------
    `ScoreSet`
        scoreset with new urn or same urn if already public.
    """
    scoreset = (
        ScoreSet.objects.filter(id=scoreset.id)
        .select_for_update(nowait=False)
        .first()
    )

    if not scoreset.has_public_urn:
        parent = (
            Experiment.objects.filter(id=scoreset.experiment.id)
            .select_for_update(nowait=False)
            .first()
        )

        if not parent.has_public_urn:
            raise AttributeError(
                "Cannot assign a public urn when parent has a temporary urn."
            )

        child_value = parent.last_child_value + 1
        scoreset.urn = "{}-{}".format(parent.urn, child_value)
        parent.last_child_value = child_value
        scoreset.save()
        parent.save(force_update=True)

        # Refresh the scoreset and nested parents
        scoreset = (
            ScoreSet.objects.filter(id=scoreset.id)
            .select_for_update(nowait=False)
            .first()
        )

    return scoreset


class ScoreSet(DatasetModel):
    """
    This is the class representing a set of scores for an experiment.
    The ScoreSet object houses all information relating to a particular
    method of variant scoring. This class assumes that all validation
    was handled at the form level, and as such performs no additional
    validation and will raise IntegrityError if there's bad input.

    Parameters
    ----------
    urn : `models.CharField`
        The urn, either temporary (auto-assigned) or public (assigned when
        published).

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

    class Meta:
        verbose_name = "ScoreSet"
        verbose_name_plural = "ScoreSets"
        permissions = (
            (PermissionTypes.CAN_VIEW, "Can view"),
            (PermissionTypes.CAN_EDIT, "Can edit"),
            (PermissionTypes.CAN_MANAGE, "Can manage"),
        )

    # ---------------------------------------------------------------------- #
    #                       Required Model fields
    # ---------------------------------------------------------------------- #
    urn = models.CharField(
        validators=[validate_mavedb_urn_scoreset],
        **UrnModel.default_urn_kwargs,
    )

    experiment = models.ForeignKey(
        to=Experiment,
        on_delete=models.PROTECT,
        null=False,
        blank=True,
        default=None,
        verbose_name="Experiment",
        related_name="scoresets",
    )

    meta_analysis_for = models.ManyToManyField(
        to="dataset.ScoreSet",
        verbose_name="Meta-analysis for",
        related_name="meta_analysed_by",
        blank=True,
        help_text=(
            "Select one or more score sets that this score set will create a "
            "meta-analysis for. Please leave the experiment field blank if "
            "this score set is a meta-analysis."
        ),
    )

    licence = models.ForeignKey(
        to=Licence,
        on_delete=models.DO_NOTHING,
        verbose_name="Licence",
        related_name="attached_scoresets",
        default=None,
        null=True,
        blank=True,
    )

    dataset_columns = JSONField(
        verbose_name="Dataset columns",
        default=default_dataset,
        validators=[validate_scoreset_json],
    )

    replaces = models.OneToOneField(
        to="dataset.ScoreSet",
        on_delete=models.SET_NULL,
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

    data_usage_policy = models.TextField(
        null=True,
        default="",
        blank=True,
        verbose_name="Data usage policy",
        validators=[WordLimitValidator(250)],
    )

    # version tags as TextField attribute
    variant_format = models.TextField(
        default="MaveDB v1.x",  # add conditional statement here
        verbose_name="Variant format is Mave 2.0 compatible",
    )

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    @transaction.atomic
    def save(self, *args, **kwargs):
        # all new uploads should have the new variant tag
        self.variant_format = "MaveDB v2.x"

        if self.licence is None:
            self.licence = Licence.get_default()
        return super().save(*args, **kwargs)

    @classmethod
    def tracked_fields(cls):
        return super().tracked_fields() + (
            "licence",
            "data_usage_policy",
            "variant_format",
        )

    # todo: add tests for below methods
    @classmethod
    def annotate_meta_children_count(cls, queryset=None):
        if queryset is None:
            queryset = cls.objects

        field_name = "meta_analysis_child_count"
        return field_name, queryset.annotate(
            **{field_name: Count("meta_analysis_for")}
        )

    @classmethod
    def meta_analyses(cls, queryset=None):
        if queryset is None:
            queryset = cls.objects

        field, objects = cls.annotate_meta_children_count(queryset)
        # Return un-annotated queryset
        return queryset.filter(pk__in=objects.filter(**{f"{field}__gt": 0}))

    @classmethod
    def non_meta_analyses(cls, queryset=None):
        if queryset is None:
            queryset = cls.objects

        return queryset.exclude(pk__in=cls.meta_analyses(queryset))

    @property
    def parent(self):
        return getattr(self, "experiment", None)

    @property
    def children(self):
        return self.variants.all()

    @property
    def is_meta_analysis(self):
        return self.meta_analysis_for.count() > 0

    @property
    def is_meta_analysed(self):
        return self.meta_analysed_by.count() > 0

    @property
    def has_variants(self):
        return hasattr(self, "variants") and self.variants.count() > 0

    @property
    def variant_count(self):
        return self.variants.count()

    @property
    def has_protein_variants(self):
        return self.variants.exclude(hgvs_pro=None).count()

    @property
    def has_uniprot_metadata(self):
        return hasattr(self, "target") and getattr(
            self.target, "uniprot_id", None
        )

    def delete_variants(self):
        self.variants.all().delete()
        self.dataset_columns = default_dataset()
        self.last_child_value = 0
        self.save()
        return self

    def get_target(self):
        if not hasattr(self, "target"):
            return None
        return self.target

    def get_target_organisms(self):
        if not self.get_target():
            return set()
        return set(
            [
                g.get_organism_name()
                for g in self.get_target().get_reference_genomes()
            ]
        )

    def get_display_target_organisms(self):
        if not self.get_target():
            return set()
        return set(
            sorted(
                [
                    r.format_reference_genome_organism_html()
                    for r in self.get_target().get_reference_maps()
                ]
            )
        )

    def get_url(self, request=None):
        base = base_url(request)
        return base + reverse("dataset:scoreset_detail", args=(self.urn,))

    # JSON field related methods
    # ---------------------------------------------------------------------- #
    @property
    def score_columns(self):
        return [
            constants.hgvs_nt_column,
            constants.hgvs_splice_column,
            constants.hgvs_pro_column,
        ] + self.dataset_columns[constants.score_columns]

    @property
    def count_columns(self):
        return [
            constants.hgvs_nt_column,
            constants.hgvs_splice_column,
            constants.hgvs_pro_column,
        ] + self.dataset_columns[constants.count_columns]

    @property
    def has_score_dataset(self):
        return (
            self.has_variants
            and len(self.dataset_columns[constants.score_columns]) >= 1
        )

    @property
    def has_count_dataset(self):
        return (
            self.has_variants
            and len(self.dataset_columns[constants.count_columns]) > 0
        )

    @property
    def has_metadata(self):
        return len(self.extra_metadata) > 0

    @property
    def primary_hgvs_column(self):
        # Primary hgvs column will be _nt whenever there are any variants
        # with their `hgvs_nt` field as not None.
        if self.children.filter(hgvs_nt=None).count() == self.children.count():
            return constants.hgvs_pro_column
        return constants.hgvs_nt_column

    # replaced_by/replaces chain traversal
    # ---------------------------------------------------------------------- #
    @property
    def has_replacement(self):
        return getattr(self, "replaced_by", None) is not None

    @property
    def replaces_previous(self):
        return getattr(self, "replaces", None) is not None

    # ----- Return public/private versions
    @property
    def current_version(self):
        instance = self
        while instance.next_version is not None:
            instance = instance.next_version
        return instance

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

    # ---- Return public version only
    @property
    def current_public_version(self):
        instance = self
        while instance.next_version is not None:
            if instance.next_version.private:
                break
            else:
                instance = instance.next_version
        return instance

    @property
    def next_public_version(self):
        if self.has_replacement and not self.next_version.private:
            return self.next_version
        return None

    @property
    def previous_public_version(self):
        instance = self
        public_versions = []
        while instance.previous_version is not None:
            if not instance.previous_version.private:
                public_versions.append(instance.previous_version)
            instance = instance.previous_version
        if not public_versions:
            return None
        else:
            return public_versions[-1]

    # ----- Returns version suitable for user
    def get_version(self, attr, public_attr, user=None):
        """
        Get the version of this scoreset described by `attr`. Checks if an
        authenticated user is present in the context. If one is present and
        the version is private, checks if user is a contributor. If so, returns
        this private version, otherwise returns the public version defined
        by `public_attr`, which may be `None`.
        """
        version = getattr(self, attr)
        public_version = getattr(self, public_attr)
        if user is None or version is None:
            return public_version
        elif version.private and user in version.contributors:
            return version
        else:
            return public_version

    def get_next_version(self, user=None):
        """
        Get the next version of this scoreset. Checks if an authenticated
        user is present in the context. If one is present and the next
        version is private, checks if user is a contributor. If so, returns
        the next private version, otherwise returns the next public
        version, which may be `None`.
        """
        return self.get_version("next_version", "next_public_version", user)

    def get_previous_version(self, user=None):
        """
        Get the previous version of this scoreset. Checks if an authenticated
        user is present in the context. If one is present and the previous
        version is private, checks if user is a contributor. If so, returns
        the previous private version, otherwise returns the next previous public
        version, which may be `None`.
        """
        return self.get_version(
            "previous_version", "previous_public_version", user
        )

    def get_current_version(self, user=None):
        """
        Get the current version of this scoreset. Checks if an authenticated
        user is present in the context. If one is present and the current
        version is private, checks if user is a contributor. If so, returns
        the current private version, otherwise returns the most current public
        version.
        """
        return self.get_version(
            "current_version", "current_public_version", user
        )

    def get_error_message(self):
        """
        Return the error message associated with the most recent task submitted
        for this scoreset.
        """
        failedtask = (
            FailedTask.objects.filter(kwargs__icontains=self.urn)
            .order_by("-modification_date")
            .first()
        )
        if failedtask:
            if failedtask.exception_class == SoftTimeLimitExceeded.__name__:
                return "Soft time limit was exceeded."
            msg = (
                failedtask.exception_msg.replace(
                    str(failedtask.exception_class), ""
                )
                .replace("(", "")
                .replace(")", "")
            )
            if not msg:
                return str(failedtask.exception_class)
            return msg

        return "An error occurred during processing. Please contact support."


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
