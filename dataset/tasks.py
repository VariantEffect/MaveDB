from django.db import transaction
from django.contrib.auth import get_user_model

from celery.utils.log import get_task_logger

from core.tasks import BaseTask

from mavedb import celery_app

from variant.models import Variant
from variant.utilities import convert_df_to_variant_records

from dataset import constants
from dataset.utilities import delete_instance as delete_instance_util
from dataset.utilities import get_model_by_urn

from . import models
from .utilities import publish_dataset

User = get_user_model()
logger = get_task_logger('dataset.tasks')

# Overrides global soft time limit of 60 seconds. If this limit is exceeded
# a SoftTimeLimitExceeded exception will be raised.
# SOFT_TIME_LIMIT = settings.task_soft_time_limit


class BaseDatasetTask(BaseTask):
    """
    Base task which handles the `on_success`, `on_failure` and `run`
    callbacks.
    
    Notifies users and sets the processing status of instances appropriately
    according to task status.
    """
    notify_callback = 'notify_user_submission_status'
    description=None
    
    def run(self, *args, **kwargs):
        raise NotImplementedError()
    
    def notify_submitting_user(self, **kwargs):
        if self.user is not None and self.notify_callback is not None:
            getattr(self.user.profile, self.notify_callback)(**kwargs)
            
    def on_success(self, retval, task_id, args, kwargs):
        if self.instance is not None:
            # Reset to success and not fail. Setting to fail will
            # prevent other actions.
            self.instance.refresh_from_db()
            self.instance.processing_state = constants.success
            self.instance.save()
        self.notify_submitting_user(
            success=True, task_id=task_id,
            description=self.description.format(urn=self.urn)
        )
        return super().on_success(retval, task_id, args, kwargs)
        
    def on_failure(self, exc, task_id, args, kwargs, einfo, user=None):
        if self.instance is not None:
            # Reset to success and not fail. Setting to fail will
            # prevent other actions.
            self.instance.refresh_from_db()
            self.instance.processing_state = constants.failed
            self.instance.save()
        self.notify_submitting_user(
            success=False, task_id=task_id,
            description=self.description.format(urn=self.urn)
        )
        return super().on_failure(
            exc, task_id, args, kwargs, einfo, user=self.user)
        

class BaseCreateVariantsTask(BaseDatasetTask):
    description = "create a new entry with urn {urn}."
    
    def run(self, *args, **kwargs):
        return create_variants(*args, **kwargs)
  

class BasePublishTask(BaseDatasetTask):
    description = "publish the entry {urn}."
    
    def run(self, *args, **kwargs):
        return publish_scoreset(*args, **kwargs)
    
    def on_failure(self, exc, task_id, args, kwargs, einfo, user=None):
        retval = super().on_failure(
            exc, task_id, args, kwargs, einfo, user=None)
        if self.instance is not None and not self.instance.has_public_urn:
            self.instance.private = True
            self.instance.save()
            
            if not self.instance.parent.has_public_urn:
                experiment = self.instance.parent
                experiment.private = True
                experiment.save()
                
            if not self.instance.parent.parent.has_public_urn:
                experimentset = self.instance.parent.parent
                experimentset.private = True
                experimentset.save()
                
        return retval
    

class BaseDeleteTask(BaseDatasetTask):
    description = "delete the entry {urn}."
    
    def run(self, *args, **kwargs):
        return delete_instance(*args, **kwargs)
    
    def on_failure(self, exc, task_id, args, kwargs, einfo, user=None):
        retval = super().on_failure(
            exc, task_id, args, kwargs, einfo, user=None)
        if self.instance is not None:
            # Reset to success and not fail. Setting to fail will
            # prevent other actions.
            self.instance.refresh_from_db()
            self.instance.processing_state = constants.success
            self.instance.save()
        return retval
    

# Note: don't remove unused arguments for the tasks below. They are required
# for the on_failure and on_success callbacks.
@celery_app.task(
    bind=True,
    ignore_result=True,
    base=BasePublishTask,
)
def publish_scoreset(self, user_pk, scoreset_urn):
    """
    Celery task to that publishes a `models.scoreset.ScoreSet` instance.
    
    Parameters
    ----------
    self : `BasePublishTask`
        Bound when celery calls this task.
    user_pk : int
        Primary key (id) of the submitting user.
    scoreset_urn : str
        The urn of the scoreset to publish.

    Returns
    -------
    `models.scoreset.ScoreSet`
    """
    # Bind task instance variables
    self.urn = scoreset_urn
    self.instance = None
    self.user = None
    
    # Look for instances. This might throw an ObjectDoesNotExist exception.
    # Bind ORM objects if they were found
    self.user = User.objects.get(pk=user_pk)
    self.instance = models.scoreset.ScoreSet.objects.get(urn=self.urn)
    
    with transaction.atomic():
        self.scoreset = publish_dataset(dataset=self.instance, user=self.user)
        self.urn = self.instance.urn
    return self.instance


@celery_app.task(
    bind=True,
    ignore_result=True,
    base=BaseDeleteTask,
)
def delete_instance(self, user_pk, urn):
    """
    Celery task to that delete a `models.base.DatasetModel` instance.

    Parameters
    ----------
    self : `BaseDeleteTask`
        Bound when celery calls this task.
    user_pk : int
        Primary key (id) of the submitting user.
    urn : str
        The urn of the instance to delete.

    Returns
    -------
    None
    """
    # Bind task instance variables
    self.urn = urn
    self.instance = None
    self.user = None
    
    # Look for instances. This might throw an ObjectDoesNotExist exception.
    # Bind ORM objects if they were found
    self.user = User.objects.get(pk=user_pk)
    self.instance = get_model_by_urn(self.urn)
    
    if self.instance.children.count() and \
            not isinstance(self.instance, models.scoreset.ScoreSet):
        raise ValueError("{} has children and cannot be deleted.".format(
            self.urn))
    with transaction.atomic():
        return delete_instance_util(self.instance)


@celery_app.task(
    bind=True,
    ignore_result=True,
    base=BaseCreateVariantsTask,
    serializer='pickle',
)
def create_variants(self, user_pk, scoreset_urn,
                    scores_records, counts_records, index, dataset_columns):
    """
    Celery task to that creates and associates `variant.model.Variant` instances
    parsed/validated during upload to a `models.scoreset.ScoreSet` instance.

    Parameters
    ----------
    self : `BaseCreateVariantsTask`
        Bound when celery calls this task.
    user_pk : int
        Primary key (id) of the submitting user.
    scoreset_urn : str
        The urn of the instance to associate variants to.
    scores_records : str
        JSON formatted dataframe that has been `records` oriented.
    counts_records :
        JSON formatted dataframe that has been `records` oriented.
    index : str
        HGVS column to use as the index when matching up variant data between
        scores and counts.
    dataset_columns : dict
        Contians keys `scores` and `counts`. The values are lists of strings
        indicating the columns to be expected in the variants for this dataset.

    Returns
    -------
    `models.scoreset.ScoreSet`
    """
    # Bind task instance variables
    self.urn = scoreset_urn
    self.instance = None
    self.user = None
    # Look for instances. This might throw an ObjectDoesNotExist exception.
    # Bind ORM objects if they were found
    self.user = User.objects.get(pk=user_pk)
    self.instance = models.scoreset.ScoreSet.objects.get(urn=scoreset_urn)

    logger.info('Sending scores dataframe with {} rows.'.format(
        len(scores_records)))
    logger.info('Sending counts dataframe with {} rows.'.format(
        len(counts_records)))
    logger.info('Formatting variants for {}'.format(self.urn))
    variants = convert_df_to_variant_records(
        scores_records, counts_records, index)
    
    if variants:
        logger.info('{}:{}'.format(self.urn, variants[-1]))
    
    with transaction.atomic():
        logger.info('Deleting existing variants for {}'.format(self.urn))
        self.instance.delete_variants()
    
        logger.info('Creating variants for {}'.format(self.urn))
        Variant.bulk_create(self.instance, variants)
        
        logger.info('Saving {}'.format(self.urn))
        self.instance.dataset_columns = dataset_columns
        self.instance.save()
    
    return self.instance
