import logging
import datetime
from string import ascii_uppercase

from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models, IntegrityError
from django.db.models.signals import pre_save, post_save

from .validators import valid_exp_accession, valid_expset_accession
from .validators import valid_wildtype_sequence

from accounts.models import PermissionTypes, GroupTypes
from accounts.models import make_all_groups_for_instance

from main.models import (
    Keyword, ExternalAccession,
    TargetOrganism, ReferenceMapping
)
from main.utils.pandoc import convert_md_to_html

logger = logging.getLogger("django")
positive_integer_validator = MinValueValidator(limit_value=0)


class ExperimentSet(models.Model):
    """
    This is the class representing a set of related Experiments. Related
    experiments are those that generally had the same data collection
    methodology, same target, target organism etc, but differed in
    the experimental condition and scoring process.

    Parameters
    ----------
    accession : `models.CharField`
        The accession in the format 'EXPSXXXXXX'
    creation_date : `models.DataField`
        Data of instantiation in yyyy-mm-dd format.
    last_edit_date : `models.DataField`
        Data of instantiation in yyyy-mm-dd format. Updates everytime `save`
        is called.
    publish_date : `models.DataField`
        Data of instantiation in yyyy-mm-dd format. Updates when `publish` is
        called.
    approved : `models.BooleanField`
        The approved status, as seen by the database admin. Instances are
        created by default as not approved and must be manually checked
        before going live.
    last_used_suffix : `models.IntegerField`
        Min value of 0. Counts how many variants have been associated with
        this dataset. Must be manually incremented everytime, but this might
        change to a post_save signal
    private : `models.BooleanField`
        Whether this experiment should be private and viewable only by
        those approved in the permissions.
    metadata : `models.JSONField`
        The free-form json metadata that might be associated with this
        experimentset.

    Methods
    -------
    """

    ACCESSION_DIGITS = 6
    ACCESSION_PREFIX = "EXPS"

    class Meta:
        ordering = ['-creation_date']
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
    accession = models.CharField(
        unique=True, default=None, blank=True, null=True,
        max_length=ACCESSION_DIGITS + len(ACCESSION_PREFIX),
        verbose_name="Accession", validators=[valid_expset_accession])

    last_used_suffix = models.CharField(
        blank=True, null=True, default="", max_length=64)

    creation_date = models.DateField(
        blank=False, null=False, default=datetime.date.today,
        verbose_name="Created on")
    last_edit_date = models.DateField(
        blank=False, null=False, default=datetime.date.today,
        verbose_name="Last edited on")
    publish_date = models.DateField(
        blank=False, null=True, default=None,
        verbose_name="Published on")

    approved = models.BooleanField(
        blank=False, null=False, default=False, verbose_name="Approved")

    private = models.BooleanField(
        blank=False, null=False, default=True, verbose_name="Private")

    metadata = JSONField(blank=True, default={}, verbose_name="Metadata")

# ---------------------------------------------------------------------- #
#                       Methods
# ---------------------------------------------------------------------- #
    def __str__(self):
        return str(self.accession)

    def save(self, *args, **kwargs):
        super(ExperimentSet, self).save(*args, **kwargs)

        # This will not work if manually setting accession.
        # Replace this section with POST/PRE save signal.
        self.last_edit_date = datetime.date.today()

        if self.accession is not None:
            valid_expset_accession(self.accession)
        else:
            digit_bit = str(self.pk)
            digit_suffix = digit_bit.zfill(self.ACCESSION_DIGITS)
            accession = "{}{}".format(self.ACCESSION_PREFIX, digit_suffix)
            self.accession = accession
            self.save()

    def get_authors(self):
        return ', '.join([])

    def publish(self):
        self.private = False
        self.publish_date = datetime.date.today()
        self.save()

    def next_experiment_suffix(self):
        if not self.last_used_suffix:
            suffix = ascii_uppercase[0]
        else:
            last_used = self.last_used_suffix
            index = ascii_uppercase.index(last_used[0].upper()) + 1
            times_to_repeat = len(last_used)
            if index >= len(ascii_uppercase):
                times_to_repeat += 1
            next_index = index % len(ascii_uppercase)
            suffix = ascii_uppercase[next_index] * times_to_repeat
        return suffix


class Experiment(models.Model):
    """
    This is the class representing an Experiment. The experiment object
    houses all information relating to a particular experiment up to the
    scoring of its associated variants. This class assumes that all validation
    was handled at the form level, and as such performs no additonal
    validation and will raise IntegreityError if there's bad input.

    Parameters
    ----------
    accession : `models.CharField`
        The accession in the format 'EXPXXXXXX[A-Z]+'
    experimentset : `models.ForeignKey`.
        The experimentset is instance assciated with. New `ExperimentSet` is
        created if this is not provided.
    target : `models.CharField`
        The gene target this experiment examines.
    wt_sequence : `models.CharField`
        The wild type DNA sequence that is related to the `target`. Will
        be converted to upper-case upon instantiation.
    creation_date : `models.DataField`
        Data of instantiation in yyyy-mm-dd format.
    last_edit_date : `models.DataField`
        Data of instantiation in yyyy-mm-dd format. Updates everytime `save`
        is called.
    publish_date : `models.DataField`
        Data of instantiation in yyyy-mm-dd format. Updates when `publish` is
        called.
    approved : `models.BooleanField`
        The approved status, as seen by the database admin. Instances are
        created by default as not approved and must be manually checked
        before going live.
    last_used_suffix : `models.IntegerField`
        Min value of 0. Counts how many variants have been associated with
        this dataset. Must be manually incremented everytime, but this might
        change to a post_save signal
    private : `models.BooleanField`
        Whether this experiment should be private and viewable only by
        those approved in the permissions.
    abstract : `models.TextField`
        A markdown text blob.
    method_desc : `models.TextField`
        A markdown text blob of the scoring method.
    doi_id : `models.CharField`
        The DOI for this experiment if any.
    sra_id : `models.CharField`
        The SRA for this experiment if any.
    metadata : `models.JSONField`
        The free-form json metadata that might be associated with this
        experiment.
    keywords : `models.ManyToManyField`
        The keyword instances that are associated with this instance.
    external_accession : `models.ManyToManyField`
        Any external accessions that relate to `target`.
    target_organism : `models.ManyToManyField`
        The `TargetOrganism` instance that the target comes from. There should
        only be one associated per `Experiment` instance.

    Methods
    -------
    """
    # ---------------------------------------------------------------------- #
    #                       Class members/functions
    # ---------------------------------------------------------------------- #
    ACCESSION_DIGITS = 6
    ACCESSION_PREFIX = "EXP"

    class Meta:
        ordering = ['-creation_date']
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
    accession = models.CharField(
        unique=True, default=None, blank=True, null=True, max_length=64,
        verbose_name="Accession", validators=[valid_exp_accession])

    experimentset = models.ForeignKey(
        to=ExperimentSet, on_delete=models.PROTECT, null=True,
        default=None, blank=True, verbose_name="Experiment Set"
    )

    creation_date = models.DateField(
        blank=False, null=False, default=datetime.date.today,
        verbose_name="Created on")
    last_edit_date = models.DateField(
        blank=False, null=False, default=datetime.date.today,
        verbose_name="Last edited on")
    publish_date = models.DateField(
        blank=False, null=True, default=None,
        verbose_name="Published on")

    last_used_suffix = models.IntegerField(
        default=0, validators=[positive_integer_validator])

    approved = models.BooleanField(
        blank=False, null=False, default=False, verbose_name="Approved")

    private = models.BooleanField(
        blank=False, null=False, default=True, verbose_name="Private")

    wt_sequence = models.TextField(
        default=None, blank=False, null=False,
        verbose_name="Wild type sequence",
        validators=[valid_wildtype_sequence])

    target = models.CharField(
        default=None, blank=False, null=False, verbose_name="Target",
        max_length=128
    )

    # ---------------------------------------------------------------------- #
    #                       Optional Model fields
    # ---------------------------------------------------------------------- #
    abstract = models.TextField(
        blank=True, default="", verbose_name="Abstract")
    method_desc = models.TextField(
        blank=True, default="", verbose_name="Method description")
    sra_id = models.CharField(
        blank=True, default="", verbose_name="SRA identifier",
        max_length=128
    )
    doi_id = models.CharField(
        blank=True, default="", verbose_name="DOI identifier",
        max_length=128
    )
    metadata = JSONField(blank=True, default={}, verbose_name="Metadata")

    keywords = models.ManyToManyField(Keyword, blank=True)
    external_accessions = models.ManyToManyField(ExternalAccession, blank=True)
    target_organism = models.ManyToManyField(TargetOrganism, blank=True)

    # ---------------------------------------------------------------------- #
    #                       Methods
    # ---------------------------------------------------------------------- #
    # TODO: add helper functions to check permision bit and author bits
    def __str__(self):
        return str(self.accession)

    def save(self, *args, **kwargs):
        super(Experiment, self).save(*args, **kwargs)
        # This will not work if manually setting accession.
        # Replace this section with POST/PRE save signal.
        self.last_edit_date = datetime.date.today()
        self.wt_sequence = self.wt_sequence.upper()

        if self.accession is not None:
            valid_exp_accession(self.accession)
        else:
            expset = None
            if self.experimentset is None:
                expset = ExperimentSet.objects.create()
                self.experimentset = expset

            parent = self.experimentset
            suffix = parent.next_experiment_suffix()
            accession = "{}{}".format(
                parent.accession.replace(
                    parent.ACCESSION_PREFIX, self.ACCESSION_PREFIX
                ),
                suffix
            )
            parent.last_used_suffix = suffix
            parent.save()
            self.accession = accession
            self.save()

    def publish(self):
        self.private = False
        self.publish_date = datetime.date.today()
        self.save()

    def get_keywords(self):
        return ', '.join([kw.text for kw in self.keywords.all()])

    def get_authors(self):
        return ', '.join([])

    def get_other_accessions(self):
        return ', '.join([a.text for a in self.external_accessions.all()])

    def get_ref_mappings(self):
        return [a for a in self.referencemapping_set.all()]

    def get_target_organism(self):
        if self.target_organism.count():
            return self.target_organism.all()[0].text

    def next_scoreset_suffix(self):
        return self.last_used_suffix + 1

    def md_abstract(self):
        return convert_md_to_html(self.abstract)

    def md_method_desc(self):
        return convert_md_to_html(self.method_desc)


# --------------------------------------------------------------------------- #
#                               POST SAVE
# --------------------------------------------------------------------------- #
@receiver(post_save, sender=ExperimentSet)
def create_groups_for_experimentset(sender, instance, **kwargs):
    make_all_groups_for_instance(instance)


@receiver(post_save, sender=Experiment)
def create_groups_for_experiment(sender, instance, **kwargs):
    make_all_groups_for_instance(instance)
