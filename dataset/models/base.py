import datetime

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.core.validators import MinValueValidator
from django.db import models, transaction

from core.mixins import SingletonMixin
from core.models import TimeStampedModel

from accounts.mixins import GroupPermissionMixin
from accounts import permissions

from core.utilities import pandoc
from metadata.models import (
    Keyword, SraIdentifier, DoiIdentifier,
    PubmedIdentifier, ExternalIdentifier
)
from urn.models import UrnModel

from dataset import constants


User = get_user_model()
child_attr_map = {
    'ExperimentSet': ('experiments', 'Experiment', 'dataset'),
    'Experiment': ('scoresets', 'ScoreSet', 'dataset'),
    'ScoreSet': ('variants', 'Variant', 'variant'),
    'Variant': (None, None, None)
}
parent_attr_map = {
    'ExperimentSet': None,
    'Experiment': 'experimentset',
    'ScoreSet': 'experiment',
    'Variant': 'scoreset'
}


def rename_groups(dataset):
    admins = dataset.administrators()
    editors = dataset.editors()
    viewers = dataset.viewers()
    # The old groups associated with the tmp urn must be deleted
    permissions.delete_all_groups_for_instance(dataset)
    # Re-assign contributors to the new groups.
    dataset.add_administrators(admins)
    dataset.add_editors(editors)
    dataset.add_viewers(viewers)
    return dataset


class PublicDatasetCounter(SingletonMixin, TimeStampedModel):
    """
    Keeps track of the number of public datasets for each model type.
    """
    experimentsets = models.IntegerField(default=0)
    

class DatasetModel(UrnModel, GroupPermissionMixin):
    """
    This is the abstract base class for ExperimentSet, Experiment, and
    ScoreSet classes. It includes permissions, creation/edit details, shared
    metadata, and behaviors for displaying and formatting the metadata.

    Parameters
    ----------
    creation_date : `models.DataField`
        Data of instantiation in yyyy-mm-dd format.

    modification_date : `models.DataField`
        Data of instantiation in yyyy-mm-dd format. Updates everytime `save`
        is called.

    publish_date : `models.DataField`
        Data of instantiation in yyyy-mm-dd format. Updates when `publish` is
        called.

    created_by : `models.ForeignKey`
        User the instance was created by.

    modified_by : `models.ForeignKey`
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

    short_description : `models.CharField`
        A short plain text description.

    title : `models.CharField`
        A short plain text title.

    keywords : `models.ManyToManyField`
        Associated `Keyword` objects for this entry.

    sra_ids : `models.ManyToManyField`
        Associated `ExternalIdentifier` objects for this entry that map to the
        NCBI Sequence Read Archive (https://www.ncbi.nlm.nih.gov/sra).

    doi_ids : `models.ManyToManyField`
        Associated `ExternalIdentifier` objects for this entry that map to
        Digital Object Identifiers (https://www.doi.org). These are intended to
        be used for data objects rather than publications.

    pubmed_ids : `models.ManyToManyField`
        Associated `ExternalIdentifier` objects for this entry that map to
        NCBI PubMed identifiers (https://www.ncbi.nlm.nih.gov/pubmed). These
        will be formatted and displayed as publications.
    """
    M2M_FIELD_NAMES = (
        'keywords',
        'doi_ids',
        'pubmed_ids',
        'sra_ids',
    )
    STATUS_CHOICES = (
        (constants.processing, constants.processing),
        (constants.success, constants.success),
        (constants.failed, constants.failed),
    )

    class Meta:
        abstract = True
        ordering = ['-creation_date']

    @classmethod
    def class_name(cls):
        return cls.__name__.lower()

    @classmethod
    def tracked_fields(cls):
        return (
            "title", "short_description", "abstract_text", "method_text",
            "keywords", "sra_ids", "doi_ids", "pubmed_ids",
        )

    # ---------------------------------------------------------------------- #
    #                       Model fields
    # ---------------------------------------------------------------------- #
    publish_date = models.DateField(
        blank=True,
        null=True,
        default=None,
        verbose_name="Published on",
    )

    modified_by = models.ForeignKey(
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

    processing_state = models.CharField(
        blank=True,
        null=True,
        default=None,
        max_length=32,
        verbose_name="Processing state",
        choices=STATUS_CHOICES
    )

    approved = models.BooleanField(
        blank=True,
        null=False,
        default=False,
        verbose_name="Approved",
    )

    private = models.BooleanField(
        blank=True,
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
    short_description = models.TextField(
        blank=False,
        default="",
        verbose_name="Short description",
    )
    title = models.CharField(
        blank=False,
        default="",
        verbose_name="Short title",
        max_length=250
    )

    # ---------------------------------------------------------------------- #
    #                       Optional Model fields
    # ---------------------------------------------------------------------- #
    keywords = models.ManyToManyField(
        Keyword, blank=True,
        verbose_name='Keywords',
        related_name='associated_%(class)ss',)
    sra_ids = models.ManyToManyField(
        SraIdentifier, blank=True,
        verbose_name='SRA Identifiers',
        related_name='associated_%(class)ss',)
    doi_ids = models.ManyToManyField(
        DoiIdentifier, blank=True,
        verbose_name='DOI Identifiers',
        related_name='associated_%(class)ss',)
    pubmed_ids = models.ManyToManyField(
        PubmedIdentifier, blank=True,
        verbose_name='PubMed Identifiers',
        related_name='associated_%(class)ss',)

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
        if save_parents:
            self.save_parents(*args, **kwargs)
        super().save(*args, **kwargs)
        return self

    @transaction.atomic
    def save_children(self):
        if self.children:
            for child in self.children:
                child.save()
       
    def save_parents(self, *args, **kwargs):
        if hasattr(self, 'experiment'):
            self.experiment.save(*args, **kwargs)
            self.experiment.save_parents(*args, **kwargs)
        if hasattr(self, 'experimentset'):
            self.experimentset.save(*args, **kwargs)

    def set_modified_by(self, user, propagate=False):
        if propagate:
            self.propagate_set_value('modified_by', user)
        else:
            self.modified_by = user

    def set_publish_date(self, date=None, propagate=False):
        if not date:
            date = datetime.date.today()
        if propagate:
            self.propagate_set_value('publish_date', date)
        else:
            self.publish_date = date

    def set_created_by(self, user, propagate=False):
        if propagate:
            self.propagate_set_value('created_by', user)
        else:
            self.created_by = user

    def approve(self, propagate=True):
        if propagate:
            self.propagate_set_value('approved', True)
        else:
            self.approved = True

    def md_abstract(self):
        return pandoc.convert_md_to_html(self.abstract_text)

    def md_method(self):
        return pandoc.convert_md_to_html(self.method_text)

    def get_title(self):
        return self.title

    def get_description(self):
        return self.short_description

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
            self.pubmed_ids.add(instance)
        elif isinstance(instance, DoiIdentifier):
            self.doi_ids.add(instance)
        else:
            raise TypeError(
                "Missing case for class `{}`.".format(
                    type(instance).__name__
                ))

    def clear_m2m(self, field_name):
        getattr(self, field_name).clear()

    def clear_keywords(self):
        self.clear_m2m('keywords')

    @property
    def parent(self):
        attr = parent_attr_map[self.__class__.__name__]
        if attr is not None and hasattr(self, attr):
            return getattr(self, attr)
        else:
            return None

    @property
    def children(self):
        attr, model_name, app_label = child_attr_map[self.__class__.__name__]
        if hasattr(self, attr):
            return getattr(self, attr).order_by('urn')
        else:
            if model_name is None:
                return None
            else:
                model = apps.get_model(app_label, model_name=model_name)
                return model.objects.none()
