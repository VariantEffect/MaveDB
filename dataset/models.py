import logging
import datetime
import reversion
import string

from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.core.validators import MinValueValidator

from django.contrib.postgres.fields import JSONField
from django.db import models, transaction
from django.db.models.signals import post_save, pre_delete

from accounts.mixins import GroupPermissionMixin
from accounts.permissions import (
    PermissionTypes,
    create_all_groups_for_instance,
    delete_all_groups_for_instance
)

import dataset.constants as constants

from genome.models import TargetOrganism

import main.utils.pandoc as pandoc
from main.models import Licence

from genome.validators import validate_wildtype_sequence
from metadata.models import (
    Keyword, ExternalIdentifier, SraIdentifier,
    DoiIdentifier, PubmedIdentifier
)

from urn.models import UrnModel
from urn.validators import (
    validate_mavedb_urn_scoreset,
    validate_mavedb_urn_experimentset,
    validate_mavedb_urn_experiment
)
from variant.models import Variant

from .validators import (
    validate_scoreset_json
)

User = get_user_model()
logger = logging.getLogger("django")


class DatasetModel(UrnModel, GroupPermissionMixin):
    """
    This is the abstract base class for ExperimentSet, Experiment, and
    ScoreSet classes. It includes permissions, creation/edit details, shared
    metadata, and behaviors for displaying and formatting the metadata.

    Parameters
    ----------
    creation_date : `models.DataField`
        Data of instantiation in yyyy-mm-dd format.

    last_edit_date : `models.DataField`
        Data of instantiation in yyyy-mm-dd format. Updates everytime `save`
        is called.

    publish_date : `models.DataField`
        Data of instantiation in yyyy-mm-dd format. Updates when `publish` is
        called.

    created_by : `models.ForeignKey`
        User the instance was created by.

    last_edit_by : `models.ForeignKey`
        User to make the latest change to the instance.

    approved : `models.BooleanField`
        The approved status, as seen by the database admin. Instances are
        created by default as not approved and must be manually checked
        before going live.

    private : `models.BooleanField`
        Whether this experiment should be private and viewable only by
        those approved in the permissions.

    last_child_value : `models.IntegerField`
        Min value of 0. Counts how many child entities have been associated
        with this entity. Must be incremented on child creation. Used to
        generate urn numbers for new child entries.

    extra_metadata : `models.JSONField`
        Free-form json metadata that might be associated with this entry.

    abstract_text : `models.TextField`
        A markdown text blob for the abstract.

    method_text : `models.TextField`
        A markdown text blob for the methods description.

    keywords : `models.ManyToManyField`
        Associated `Keyword` objects for this entry.

    sra_ids : `models.ManyToManyField`
        Associated `ExternalIdentifier` objects for this entry that map to the
        NCBI Sequence Read Archive (https://www.ncbi.nlm.nih.gov/sra).

    doi_ids : `models.ManyToManyField`
        Associated `ExternalIdentifier` objects for this entry that map to
        Digital Object Identifiers (https://www.doi.org). These are intended to
        be used for data objects rather than publications.

    pmid_ids : `models.ManyToManyField`
        Associated `ExternalIdentifier` objects for this entry that map to
        NCBI PubMed identifiers (https://www.ncbi.nlm.nih.gov/pubmed). These
        will be formatted and displayed as publications.
    """
    class Meta:
        abstract = True
        ordering = ['-creation_date']

    # ---------------------------------------------------------------------- #
    #                       Model fields
    # ---------------------------------------------------------------------- #
    creation_date = models.DateField(
        blank=False,
        null=False,
        default=datetime.date.today,
        verbose_name="Created on",
    )

    last_edit_date = models.DateField(
        blank=False,
        null=False,
        default=datetime.date.today,
        verbose_name="Last edited on",
    )

    publish_date = models.DateField(
        blank=False,
        null=True,
        default=None,
        verbose_name="Published on",
    )

    last_edit_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Last edited by",
        related_name='last_edited_%(class)s',
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Created by",
        related_name='last_created_%(class)s',
    )

    approved = models.BooleanField(
        blank=False,
        null=False,
        default=False,
        verbose_name="Approved",
    )

    private = models.BooleanField(
        blank=False,
        null=False,
        default=True,
        verbose_name="Private",
    )

    last_child_value = models.IntegerField(
        default=0,
        validators=[MinValueValidator(limit_value=0)],
    )

    extra_metadata = JSONField(
        blank=True,
        default={},
        verbose_name="Additional metadata",
    )

    abstract_text = models.TextField(
        blank=True,
        default="",
        verbose_name="Abstract",
    )
    method_text = models.TextField(
        blank=True,
        default="",
        verbose_name="Method description"
    )

    # ---------------------------------------------------------------------- #
    #                       Optional Model fields
    # ---------------------------------------------------------------------- #
    keywords = models.ManyToManyField(
        Keyword, blank=True, verbose_name='Keywords')
    sra_ids = models.ManyToManyField(
        SraIdentifier, blank=True, verbose_name='SRA Identifiers')
    doi_ids = models.ManyToManyField(
        DoiIdentifier, blank=True, verbose_name='DOI Identifiers')
    pmid_ids = models.ManyToManyField(
        PubmedIdentifier, blank=True, verbose_name='PubMed Identifiers')

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    def propagate_set_value(self, attr, value):
        """
        Private method for setting fields that also need to propagate upwards.
        For example, setting publishing a scoreset should also set the private
        bits on the parent experiment and experimentset.

        Parameters
        ----------
        attr : str
            Field name to set attribute of.
        value : any
            Value to set.
        """
        if hasattr(self, attr):
            self.__setattr__(attr, value)
        if hasattr(self, 'experiment'):
            self.experiment.propagate_set_value(attr, value)
        if hasattr(self, 'experimentset'):
            self.experimentset.propagate_set_value(attr, value)

    @transaction.atomic
    def save(self, save_parents=False, *args, **kwargs):
        self.last_edit_date = datetime.date.today()
        super().save(*args, **kwargs)
        if save_parents:
            self.save_parents(*args, **kwargs)

    def save_parents(self, *args, **kwargs):
        if hasattr(self, 'experiment'):
            self.experiment.save(*args, **kwargs)
            self.experiment.save_parents(*args, **kwargs)
        if hasattr(self, 'experimentset'):
            self.experimentset.save(*args, **kwargs)

    def publish(self, propagate=True):
        if propagate:
            self.propagate_set_value('private', False)
            self.propagate_set_value('publish_date', datetime.date.today())
        else:
            self.private = False
            self.publish_date = datetime.date.today()

    def set_last_edit_by(self, user, propagate=False):
        if propagate:
            self.propagate_set_value('last_edit_by', user)
        else:
            self.last_edit_by = user

    def set_created_by(self, user, propagate=False):
        if propagate:
            self.propagate_set_value('created_by', user)
        else:
            self.created_by = user

    def approve(self, propagate=True):
        if propagate:
            self.propagate_set_value('approved', False)
        else:
            self.approved = False

    def md_abstract(self):
        return pandoc.convert_md_to_html(self.abstract_text)

    def md_method(self):
        return pandoc.convert_md_to_html(self.method_text)

    def add_keyword(self, keyword):
        if not isinstance(keyword, Keyword):
            raise TypeError("`keyword` must be a Keyword instance.")
        self.keywords.add(keyword)

    def add_identifier(self, instance):
        if not isinstance(instance, ExternalIdentifier):
            raise TypeError(
                "`instance` must be an ExternalIdentifier instance.")

        if isinstance(instance, SraIdentifier):
            self.sra_ids.add(instance)
        elif isinstance(instance, PubmedIdentifier):
            self.pmid_ids.add(instance)
        elif isinstance(instance, DoiIdentifier):
            self.doi_ids.add(instance)
        else:
            raise TypeError(
                "Unsupported class `{}` for `instance`.".format(
                    type(instance).__name__
                ))

    def clear_m2m(self, field_name):
        getattr(self, field_name).clear()


@reversion.register()
class ExperimentSet(DatasetModel):
    """
    This is the class representing a set of related Experiments. Related
    experiments are those that generally had the same data collection
    methodology, same target, target organism etc, but differed in
    the experimental condition and scoring process.
    """
    # TODO: Update TRACKED_FIELDS in all classes to use inheritance
    TRACKED_FIELDS = ("private", "approved")

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
        expset_number = str(self.pk)
        padded_expset_number = expset_number.zfill(self.URN_DIGITS)
        urn = "{}{}".format(self.URN_PREFIX, padded_expset_number)
        return urn


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
        if not target_organism:
            return
        current = self.target_organism.first()
        if isinstance(target_organism, list):
            target_organism = target_organism[0]
        if current != target_organism:
            self.target_organism.remove(current)
            self.target_organism.add(target_organism)

    def get_target_organism(self):
        if self.target_organism.count():
            return self.target_organism.all()[0].text


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
        "method_text", "doi_ids", "sra_ids", "pmid_ids", "keywords",
        "license", "dataset_columns", "replaces"
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
        related_name='scoresets'
    )

    licence = models.ForeignKey(
        to=Licence, on_delete=models.DO_NOTHING,
        verbose_name="Licence",
        related_name="attached_scoresets",
        null=True,
        blank=True,
    )

    dataset_columns = JSONField(
        verbose_name="Dataset columns",
        default=dict({
            constants.score_columns: [],
            constants.count_columns: [],
        }),
        validators=[validate_scoreset_json]
    )

    replaces = models.OneToOneField(
        to='dataset.ScoreSet',
        on_delete=models.DO_NOTHING,
        null=True,
        verbose_name="Replaces",
        related_name="replaced_by",
        blank=True,
    )

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.experiment is None:
            self.experiment = Experiment.objects.create()
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
    def has_variants(self):
        return self.variants.count() > 0

    def get_variants(self):
        if self.has_variants():
            return self.variants.all()
        else:
            return Variant.objects.none()

    def delete_variants(self):
        self.variants.all().delete()
        self.dataset_columns = dict({
            constants.score_columns: [],
            constants.count_columns: [],
            constants.metadata_columns: []
        })
        self.save()

    # JSON field related methods
    # ---------------------------------------------------------------------- #
    @property
    def score_columns(self):
        return self.dataset_columns[constants.score_columns]

    @property
    def count_columns(self):
        return self.dataset_columns[constants.count_columns]

    @property
    def metadata_columns(self):
        return self.dataset_columns[constants.metadata_columns]

    @property
    def has_count_dataset(self):
        return len(self.dataset_columns[constants.count_columns]) > 0

    @property
    def has_score_dataset(self):
        return len(self.dataset_columns[constants.score_columns]) > 0

    @property
    def has_metadata(self):
        return len(self.dataset_columns[constants.metadata_columns]) > 0

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
@receiver(post_save, sender=ExperimentSet)
def create_groups_for_experimentset(sender, instance, **kwargs):
    create_all_groups_for_instance(instance)


@receiver(post_save, sender=Experiment)
def create_groups_for_experiment(sender, instance, **kwargs):
    create_all_groups_for_instance(instance)


@receiver(post_save, sender=ScoreSet)
def create_permission_groups_for_scoreset(sender, instance, **kwargs):
    create_all_groups_for_instance(instance)


# --------------------------------------------------------------------------- #
#                            Post Delete
# --------------------------------------------------------------------------- #
@receiver(pre_delete, sender=ExperimentSet)
def delete_groups_for_experimentset(sender, instance, **kwargs):
    delete_all_groups_for_instance(instance)


@receiver(pre_delete, sender=Experiment)
def delete_groups_for_experiment(sender, instance, **kwargs):
    delete_all_groups_for_instance(instance)


@receiver(pre_delete, sender=ScoreSet)
def delete_permission_groups_for_scoreset(sender, instance, **kwargs):
    delete_all_groups_for_instance(instance)


