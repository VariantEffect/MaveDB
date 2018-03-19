import logging
import datetime
import reversion
import string

from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.core.validators import MinValueValidator

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models, IntegrityError, transaction
from django.db.models.signals import pre_save, post_save

from .validators import valid_mavedb_urn, MAVEDB_URN_MAX_LENGTH
from .validators import MAVEDB_EXPERIMENTSET_URN_DIGITS, MAVEDB_URN_NAMESPACE
from .validators import valid_mavedb_urn_experimentset, valid_mavedb_urn_experiment, valid_mavedb_urn_scoreset, valid_mavedb_urn_variant
from .validators import valid_wildtype_sequence

from accounts.permissions import (
    PermissionTypes,
    make_all_groups_for_instance
)
from accounts.mixins import GroupPermissionMixin

import main.utils.pandoc as pandoc

User = get_user_model()
logger = logging.getLogger("django")


class Keyword(models.Model):
    """
    This class represents a keyword that can be associated with an
    experiment or scoreset.

    Parameters
    ----------
    creation_date : `models.DateField`
        The date of instantiation.
    text : `models.TextField`
        The free-form textual representation of the keyword.
    """
    creation_date = models.DateField(blank=False, default=datetime.date.today)
    text = models.CharField(
        blank=False,
        null=False,
        default=None,
        unique=True,
        max_length=256,
        verbose_name="Keyword",
    )

    @staticmethod
    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Keyword"
        verbose_name_plural = "Keywords"

    def __str__(self):
        return self.text


class ExternalAccession(models.Model):
    """
    This class represents a textual representation of an accession from an
    external database that can be associated with a target in an experiment.

    Parameters
    ----------
    creation_date : `models.DateField`
        The date of instantiation.
    resource_accession : `models.TextField`
        The free-form textual representation of the accession from another
        database.
    resource_url : `models.URLField`
        The URL for the resource in the other database. Optional.
    database_name : `models.TextField`
        The name of the external database.
    """
    creation_date = models.DateField(blank=False, default=datetime.date.today)
    text = models.CharField(
        blank=False,
        null=False,
        default=None,
        unique=True,
        max_length=256,
        verbose_name="Accession",
    )

    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Other accession"
        verbose_name_plural = "other accessions"

    def __str__(self):
        return self.text


class TargetOrganism(models.Model):
    """
    This class represents a textual representation of a target organism
    that can be associated with an experiment.

    Parameters
    ----------
    creation_date : `models.DateField`
        The date of instantiation.
    text : `models.TextField`
        The free-form textual representation of the target organism.
    """
    creation_date = models.DateField(
        blank=False,
        default=datetime.date.today
    )
    text = models.CharField(
        blank=False,
        null=False,
        default=None,
        unique=True,
        max_length=256,
        verbose_name="Target Organism",
    )

    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Target organism"
        verbose_name_plural = "Target organisms"

    def __str__(self):
        return self.text


class AccessionModel(models.Model):
    """
    Abstract class for all entries in MAVEDB that have an accession number.

    Parameters
    ----------
    Parameters
    ----------
    accession : `models.CharField`
        The accession in the MAVEDB URN format:
        `urn:mavedb:<ExperimentSet>-<Experiment>-<ScoreSet>#<Variant>`, where
        `<ExperimentSet>` is a zero-padded eight-digit integer, `<Experiment>`
        is a lowercase letter or string of letters ('aa' follows 'z' in the rare
        case that more than 26 Experiments are associated with a single
        ExperimentSet), `<ScoreSet>` is an integer with no padding, and
        `<Variant>` is an integer with no padding.
    """
    URN_PREFIX = "urn:{}:".format(MAVEDB_URN_NAMESPACE)
    URN_DIGITS = MAVEDB_EXPERIMENTSET_URN_DIGITS

    class Meta:
        abstract = True
        ordering = ['-creation_date']

    default_kwargs = {
        "unique": True,
        "default": None,
        "blank": True,
        "null": True,
        "max_length": MAVEDB_URN_MAX_LENGTH,
        "verbose_name": "Accession",
    }

    # ---------------------------------------------------------------------- #
    #                       Model fields
    # ---------------------------------------------------------------------- #
    accession = None
#    accession = models.CharField(
#        validators=[valid_mavedb_urn],
#        **default_kwargs,
#    )

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    def __str__(self):
        return str(self.accession)

    @transaction.atomic
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.accession is None:
            self.accession = self.create_urn()
            self.save()

    def create_urn(self):
        raise NotImplementedError()


class DatasetModel(AccessionModel, GroupPermissionMixin):
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

    created_by : `models.ForeignKey`
        User the instance was created by.

    last_edit_by : `models.ForeignKey`
        User to make the latest change to the instance.

    publish_date : `models.DataField`
        Data of instantiation in yyyy-mm-dd format. Updates when `publish` is
        called.

    approved : `models.BooleanField`
        The approved status, as seen by the database admin. Instances are
        created by default as not approved and must be manually checked
        before going live.

    last_child_value : `models.IntegerField`
        Min value of 0. Counts how many child entities have been associated
        with this entity. Must be manually incremented after each child is
        added, but this might be changed to a `post_save` signal later.

    private : `models.BooleanField`
        Whether this experiment should be private and viewable only by
        those approved in the permissions.

    abstract_text : `models.TextField`
        A markdown text blob.

    method_text : `models.TextField`
        A markdown text blob of the scoring method.

    linked_doi : `models.CharField`
        Associated DOI entries, if any. Primarily used for linking to raw data.

    linked_pmid : `models.CharField`
        Associated PubMed entries, if any. Used for linking to relevant
        publications.

    extra_metadata : `models.JSONField`
        Free-form json metadata that might be associated with this entry.
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
    last_child_value = models.IntegerField(
        default=0,
        validators=[MinValueValidator(limit_value=0)],
    )

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
    sra_accessions = models.ManyToManyField(ExternalAccession, blank=True)
    doi_accessions = models.ManyToManyField(ExternalAccession, blank=True)
    pmid_accessions = models.ManyToManyField(ExternalAccession, blank=True)

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    @transaction.atomic
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # This will not work if manually setting accession.
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

    def update_keywords(self, keywords):
        kws_text = set([kw.text for kw in keywords])
        for kw in self.keywords.all():
            if kw.text not in kws_text:
                self.keywords.remove(kw)
        for kw in keywords:
            self.keywords.add(kw)

    # TODO: revisit this in the context of different URLS, different databases
    def update_external_accessions(self, accessions):
        acc_text = set([acc.text for acc in accessions])
        for acc in self.external_accessions.all():
            if acc.text not in acc_text:
                self.external_accessions.remove(acc)
        for acc in accessions:
            self.external_accessions.add(acc)

    def get_keywords(self):
        return ', '.join([kw.text for kw in self.keywords.all()])

    def get_other_accessions(self):
        return ', '.join([a.text for a in self.external_accessions.all()])


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
    accession = models.CharField(
        validators=[valid_mavedb_urn_experimentset],
        **AccessionModel.default_kwargs,
    )

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    def create_urn(self):
        expset_number = str(self.pk)
        padded_expset_number = expset_number.zfill(self.URN_DIGITS)
        accession = "{}{}".format(self.URN_PREFIX, padded_expset_number)
        return accession


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
    accession = models.CharField(
        validators=[valid_mavedb_urn_experiment],
        **AccessionModel.default_kwargs,
    )

    experimentset = models.ForeignKey(
        to=ExperimentSet,
        on_delete=models.PROTECT,
        null=True,
        default=None,
        blank=True,
        verbose_name="Experiment Set",
    )

    wt_sequence = models.TextField(
        default=None,
        blank=False,
        null=False,
        verbose_name="Wild type sequence",
        validators=[valid_wildtype_sequence],
    )

    target = models.CharField(
        default=None,
        blank=False,
        null=False,
        verbose_name="Target",
        max_length=128,
    )

    # ---------------------------------------------------------------------- #
    #                       Optional Model fields
    # ---------------------------------------------------------------------- #
    target_accessions = models.ManyToManyField(ExternalAccession, blank=True)
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

        accession = "{}-{}".format(parent.accession, suffix)

        # update parent
        parent.last_child_value = child_value
        parent.save()

        return accession

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
    accession : `models.CharField`
        The accession in the format 'SCSXXXXXX[A-Z]+.\d+'

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
        "private", "approved", "abstract", "method_desc", "doi_id", "keywords",
        "licence_type"
    )

    class Meta:
        verbose_name = "ScoreSet"
        verbose_name_plural = "ScoreSets"

    # ---------------------------------------------------------------------- #
    #                       Required Model fields
    # ---------------------------------------------------------------------- #
    accession = models.CharField(
        validators=[valid_mavedb_urn_scoreset],
        **AccessionModel.default_kwargs,
    )

    experiment = models.ForeignKey(
        to=Experiment,
        on_delete=models.PROTECT,
        null=False,
        default=None,
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
            SCORES_KEY: [],
            COUNTS_KEY: [],
        }),
        validators=[valid_scoreset_json]
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
    # TODO: add helper functions to check permision bit and author bits
    def create_urn(self):
        parent = self.experiment
        child_value = parent.last_child_value + 1

        accession = "{}-{}".format(parent.accession, child_value)

        # update parent
        parent.last_child_value = child_value
        parent.save()

        return accession

    def has_variants(self):
        return self.variant_set.count() > 0

    def get_variants(self):
        if self.has_variants():
            return self.variant_set.all()
        else:
            return Variant.objects.none()

    def delete_variants(self):
        self.variant_set.all().delete()
        self.dataset_columns = dict({
            SCORES_KEY: [], COUNTS_KEY: []
        })
        self.reset_variant_suffix()
        self.save()

    def validate_variant_data(self, variant):
        if sorted(variant.scores_columns) != sorted(self.scores_columns):
            raise ValueError("Variant scores columns '{}' do not match "
                             "ScoreSet columns '{}'.".format(
                                 variant.scores_columns, self.scores_columns))
        if sorted(variant.counts_columns) != sorted(self.counts_columns):
            raise ValueError("Variant counts columns '{}' do not match "
                             "ScoreSet columns '{}'.".format(
                                 variant.counts_columns, self.counts_columns))

    @property
    def scores_columns(self):
        return self.dataset_columns[SCORES_KEY]

    @property
    def counts_columns(self):
        return self.dataset_columns[COUNTS_KEY]

    def has_counts_dataset(self):
        return not self.dataset_columns[COUNTS_KEY] == []

    def has_replacement(self):
        return self.replaced_by is not None

    def get_current_replacement(self):
        next_instance = self
        while next_instance.has_replacement():
            next_instance = next_instance.replaced_by
        return next_instance


class Variant(AccessionModel):
    """
    This is the class representing an individual variant belonging to one
    and only one ScoreSet instance. The numerical parameters of a variant
    are held in a JSONField, which can be easily queried and extended as
    needed.

    Parameters
    ----------
    hgvs : `str`, required.
        The HGVS string belonging to the variant.

    scoreset : `ScoreSet`, required.
        The associated scoreset of the instance.

    data : `JSONField`
        The variant's numerical data.

    """
    # ---------------------------------------------------------------------- #
    #                       Class members/functions
    # ---------------------------------------------------------------------- #
    class Meta:
        verbose_name = "Variant"
        verbose_name_plural = "Variants"

    # ---------------------------------------------------------------------- #
    #                       Required Model fields
    # ---------------------------------------------------------------------- #
    accession = models.CharField(
        validators=[valid_mavedb_urn_variant],
        **AccessionModel.default_kwargs,
    )

    hgvs = models.TextField(
        blank=False,
        null=False,
        default=None,
        validators=[valid_hgvs_string],
    )

    scoreset = models.ForeignKey(
        to=ScoreSet,
        on_delete=models.PROTECT,
        null=False,
        default=None,
    )

    # ---------------------------------------------------------------------- #
    #                      Optional Model fields
    # ---------------------------------------------------------------------- #
    data = JSONField(
        verbose_name="Data columns",
        default=dict({
            SCORES_KEY: {},
            COUNTS_KEY: {},
        }),
        validators=[valid_variant_json],
    )

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    @property
    def scores_columns(self):
        return self.data[SCORES_KEY].keys()

    @property
    def counts_columns(self):
        return self.data[COUNTS_KEY].keys()

    def get_ordered_scores_data(self):
        columns = self.scoreset.scores_columns
        data = [self.data[SCORES_KEY][key] for key in columns]
        return data

    def get_ordered_counts_data(self):
        columns = self.scoreset.counts_columns
        data = [self.data[COUNTS_KEY][key] for key in columns]
        return data


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
        [s.private for s in experiment.scoreset_set.all()]
    )
    experiment_is_approved = any(
        [s.approved for s in experiment.scoreset_set.all()]
    )
    experiment.private = experiment_is_private
    experiment.approved = experiment_is_approved
    experiment.save()

    experimentset = experiment.experimentset
    experimentset_is_private = all(
        [e.private for e in experimentset.experiment_set.all()]
    )
    experimentset_is_approved = any(
        [e.approved for e in experimentset.experiment_set.all()]
    )
    experimentset.private = experimentset_is_private
    experimentset.approved = experimentset_is_approved
    experimentset.save()
