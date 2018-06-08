from django.db import transaction
from django.contrib.auth import get_user_model
from django.conf import settings

from celery.utils.log import get_task_logger

from core.utilities import notify_admins
from core.tasks import BaseTask

from mavedb import celery_app

from variant.models import Variant

from dataset import constants
from .models.scoreset import ScoreSet


User = get_user_model()
logger = get_task_logger('dataset.tasks')

# Overrides global soft time limit of 60 seconds. If this limit is exceeded
# a SoftTimeLimitExceeded exception will be raised.
SOFT_TIME_LIMIT = settings.DATASET_TASK_SOFT_TIME_LIMIT


class BaseDatasetTask(BaseTask):
    """
    Edits the scoreset processing state and emails user.
    Delegates task logging and saving to BaseTask.
    """
    def on_failure(self, exc, task_id, args, kwargs, einfo, user=None):
        if isinstance(self.scoreset, ScoreSet):
            self.scoreset.processing_state = constants.failed
            self.scoreset.save()
            
        if isinstance(self.user, User):
            self.user.profile.notify_user_upload_status(
                success=False, instance=self.scoreset,
            )
        return super(BaseDatasetTask, self).on_failure(
            exc, task_id, args, kwargs, einfo, user=self.user)


class BaseCreateVariants(BaseDatasetTask):
    """Adds in error handling callback when a task fails"""
    def on_success(self, retval, task_id, args, kwargs):
        self.scoreset.processing_state = constants.success
        self.scoreset.save()
        self.user.profile.notify_user_upload_status(
            success=True, instance=self.scoreset,
        )
        return super(BaseCreateVariants, self).on_success(
            retval, task_id, args, kwargs)


class BasePublish(BaseDatasetTask):
    """Adds in error handling callback when a task fails"""
    def on_success(self, retval, task_id, args, kwargs):
        self.scoreset.processing_state = constants.success
        self.scoreset.save()
        self.user.profile.notify_user_upload_status(
            success=True, instance=self.scoreset,
        )
        notify_admins(user=self.user, instance=self.scoreset)
        return super(BasePublish, self).on_success(
            retval, task_id, args, kwargs)
    

# Note: don't remove unused arguments for the tasks below. They are required
# for the on_failure and on_success callbacks.
@celery_app.task(bind=True, ignore_result=True,
                 base=BasePublish, soft_time_limit=SOFT_TIME_LIMIT)
def publish_scoreset(self, user_pk, scoreset_urn):
    # Bind task instance variables
    self.urn = scoreset_urn
    self.scoreset = None
    self.user = None
    
    # Look for instances. This might throw an ObjectDoesNotExist exception.
    # Bind ORM objects if they were found
    user = User.objects.get(pk=user_pk)
    self.user = user
    scoreset = ScoreSet.objects.get(urn=scoreset_urn)
    self.scoreset = scoreset
    
    with transaction.atomic():
        scoreset.publish()
        scoreset.set_modified_by(user, propagate=True)
        scoreset.save(save_parents=True)
    
    # Bound to `BasePublish`
    scoreset = ScoreSet.objects.get(urn=scoreset.urn)
    self.scoreset = scoreset  # Refreshes bound instance
    self.urn = scoreset.urn
    return scoreset


@celery_app.task(bind=True, ignore_result=True,
                 base=BaseCreateVariants, soft_time_limit=SOFT_TIME_LIMIT)
def create_variants(self, user_pk, variants, scoreset_urn, dataset_columns):
    """Bulk creates and emails the user the processing status."""
    # Bind task instance variables
    self.urn = scoreset_urn
    self.scoreset = None
    self.user = None

    # Look for instances. This might throw an ObjectDoesNotExist exception.
    # Bind ORM objects if they were found
    user = User.objects.get(pk=user_pk)
    self.user = user
    scoreset = ScoreSet.objects.get(urn=scoreset_urn)
    self.scoreset = scoreset
    
    with transaction.atomic():
        scoreset.delete_variants()
        Variant.bulk_create(scoreset, [v for _, v in variants.items()])
        scoreset.dataset_columns = dataset_columns
        scoreset.save()
    return scoreset


