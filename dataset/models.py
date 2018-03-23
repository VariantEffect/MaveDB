import logging
import datetime
import reversion
import string

from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.core.validators import MinValueValidator

from django.contrib.postgres.fields import JSONField
from django.db import models, transaction
from django.db.models.signals import post_save

from accounts.mixins import GroupPermissionMixin
from accounts.permissions import (
    PermissionTypes,
    make_all_groups_for_instance
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
        permissions = (
            (PermissionTypes.CAN_VIEW, "Can view"),
            (PermissionTypes.CAN_EDIT, "Can edit"),
            (PermissionTypes.CAN_MANAGE, "Can manage")
        )

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
    keywords = models.ManyToManyField(Keyword, blank=True)
    sra_ids = models.ManyToManyField(SraIdentifier, blank=True)
    doi_ids = models.ManyToManyField(DoiIdentifier, blank=True)
    pmid_ids = models.ManyToManyField(PubmedIdentifier, blank=True)

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    @transaction.atomic
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # This will not work if manually setting urn.
        # Replace this section with POST/PRE save signal.
        self.last_edit_date = datetime.date.today()
        self.save()

    def update_last_edit_info(self, user):
        self.last_edit_date = datetime.date.today()
        self.last_edit_by = user
        self.save()

    def publish(self):
        self.private = False
        self.publish_date = datetime.date.today()
        self.save()

    def md_abstract(self):
        return pandoc.convert_md_to_html(self.abstract_text)

    def md_methods(self):
        return pandoc.convert_md_to_html(self.method_text)

    def add_keyword(self, keyword):
        if not isinstance(keyword, Keyword):
            raise TypeError("`keyword` must be a Keyword instance.")
        self.keywords.add(keyword)

    def add_external_accession(self, instance):
        if not isinstance(instance, ExternalIdentifier):
            raise TypeError("`instance` must be an ExternalIdentifier instance.")

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

    def get_keywords(self):
        return ', '.join([kw.text for kw in self.keywords.all()])


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
        "pmid_accessions",
        "doi_accessions",
        "sra_accessions",
    )

    class Meta:
        verbose_name = "Experiment"
        verbose_name_plural = "Experiments"

    # ---------------------------------------------------------------------- #
    #                       Required Model fields
    # ---------------------------------------------------------------------- #
    urn = models.CharField(
        validators=[validate_mavedb_urn_experiment],
        **UrnModel.default_urn_kwargs,
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
        verbose_name="Target",
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
        super().save(*args, **kwargs)

        self.wt_sequence = self.wt_sequence.upper()

        if self.experimentset is None:
            self.experimentset = ExperimentSet.objects.create()

        self.save()

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
        User to make the latest change to the instnace.

    licence_type : `models.ForeignKey`
        Licence type attached to the instance.

    approved : `models.BooleanField`
        The approved status, as seen by the database admin. Instances are
        created by default as not approved and must be manually checked
        before going live.

    last_used_suffix : `models.IntegerField`
        Min value of 0. Counts how many variants have been associated with
        this dataset. Must be manually incremented everytime, but this might
        change to a post_save signal

    private : `models.BooleanField`
        Whether the dataset should be private and viewable only by
        those approved in the permissions.

    dataset_columns : `models.JSONField`
        A JSON instances with keys `scores` and `counts`. The values are
        lists of strings indicating the columns to be expected in the variants
        for this dataset.

    abstract : `models.TextField`
        A markdown text blob.

    method_desc : `models.TextField`
        A markdown text blob of the scoring method.

    doi_id : `models.CharField`
        The DOI for this scoreset if any.

    metadata : `models.JSONField`
        The free-form json metadata that might be associated with this
        scoreset.

    keywords : `models.ManyToManyField`
        The keyword instances that are associated with this instance.

    replaces : `models.ForeignKey`
        Indicates a scoreset instances that replaces the current instance.
    """
    # ---------------------------------------------------------------------- #
    #                       Class members/functions
    # ---------------------------------------------------------------------- #
    # TODO: Update TRACKED_FIELDS in all classes to use inheritance
    TRACKED_FIELDS = (
        "private", "approved", "abstract",
        "method_desc", "doi_id", "keywords",
        "licence_type"
    )

    class Meta:
        verbose_name = "ScoreSet"
        verbose_name_plural = "ScoreSets"

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
        to='scoreset.ScoreSet',
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
        super().save(*args, **kwargs)

        if self.experiment is None:
            self.experiment = Experiment.objects.create()

        self.save()

    # TODO: add helper functions to check permision bit and author bits
    def create_urn(self):
        parent = self.experiment
        child_value = parent.last_child_value + 1

        urn = "{}-{}".format(parent.urn, child_value)

        # update parent
        parent.last_child_value = child_value
        parent.save()

        return urn

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

    def has_replacement(self):
        return self.replaced_by is not None

    def get_current_replacement(self):
        next_instance = self
        while next_instance.has_replacement():
            next_instance = next_instance.replaced_by
        return next_instance


# --------------------------------------------------------------------------- #
#                               POST SAVE
# --------------------------------------------------------------------------- #
@receiver(post_save, sender=ExperimentSet)
def create_groups_for_experimentset(sender, instance, **kwargs):
    make_all_groups_for_instance(instance)


@receiver(post_save, sender=Experiment)
def create_groups_for_experiment(sender, instance, **kwargs):
    make_all_groups_for_instance(instance)


@receiver(post_save, sender=ScoreSet)
def create_permission_groups_for_scoreset(sender, instance, **kwargs):
    make_all_groups_for_instance(instance)


@receiver(post_save, sender=ScoreSet)
def propagate_private_bit(sender, instance, **kwargs):
    experiment = instance.experiment
    experiment_is_private = all(
        [s.private for s in experiment.scoresets.all()]
    )
    experiment_is_approved = any(
        [s.approved for s in experiment.scoresets.all()]
    )
    experiment.private = experiment_is_private
    experiment.approved = experiment_is_approved
    experiment.save()

    experimentset = experiment.experimentset
    experimentset_is_private = all(
        [e.private for e in experimentset.experiments.all()]
    )
    experimentset_is_approved = any(
        [e.approved for e in experimentset.experiments.all()]
    )
    experimentset.private = experimentset_is_private
    experimentset.approved = experimentset_is_approved
    experimentset.save()
