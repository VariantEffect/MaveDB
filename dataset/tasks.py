from django.db import transaction
from django.contrib.auth import get_user_model

from celery.utils.log import get_task_logger

from accounts.tasks import notify_user_upload_status
from core.tasks import email_admins, LogErrorsTask

from mavedb import celery_app

from variant.models import Variant

from dataset import constants
from .models.scoreset import ScoreSet


User = get_user_model()
logger = get_task_logger('dataset.tasks')


class BaseDatasetTask(LogErrorsTask):
    """
    Edits the scoreset processing state and emails user.
    Delegates task logging and saving to LogErrorsTask.
    """
    def on_failure(self, exc, task_id, args, kwargs, einfo, user=None):
        if isinstance(self.scoreset, ScoreSet):
            self.scoreset.processing_state = constants.failed
            self.scoreset.save()
        
        if isinstance(self.user, User):
            notify_user_upload_status.delay(
                user_pk=self.user.pk, scoreset_urn=self.urn,
                success=False, base_url=self.base_url)
        
        return super(BaseDatasetTask, self).on_failure(
            exc, task_id, args, kwargs, einfo, user=self.user)


class BaseCreateVariants(BaseDatasetTask):
    """Adds in error handling callback when a task fails"""
    def on_success(self, retval, task_id, args, kwargs):
        self.scoreset.processing_state = constants.success
        self.scoreset.save()
        notify_user_upload_status.delay(
            user_pk=self.user.pk, scoreset_urn=self.scoreset.urn,
            base_url=self.base_url, success=True
        )
        return super(BaseCreateVariants, self).on_success(
            retval, task_id, args, kwargs)


class BasePublish(BaseDatasetTask):
    """Adds in error handling callback when a task fails"""
    def on_success(self, retval, task_id, args, kwargs):
        self.scoreset.processing_state = constants.success
        self.scoreset.save()
        notify_user_upload_status.delay(
            user_pk=self.user.pk, scoreset_urn=self.scoreset.urn,
            base_url=self.base_url, success=True
        )
        email_admins.delay(
            user=self.user.pk,
            urn=self.scoreset.urn,
            base_url=self.base_url
        )
        return super(BasePublish, self).on_success(
            retval, task_id, args, kwargs)
    

# Note: don't remove unused arguments for the tasks below. They are required
# for the on_failure and on_success callbacks.
@celery_app.task(bind=True, ignore_result=True, base=BasePublish)
def publish_scoreset(self, user_pk, scoreset_urn, base_url=""):
    # Bind task instance variables
    self.urn = scoreset_urn
    self.base_url = base_url
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
    self.scoreset = scoreset # Refreshes bound instance
    self.urn = scoreset.urn
    return scoreset


@celery_app.task(bind=True, ignore_result=True, base=BaseCreateVariants)
def create_variants(self, user_pk, variants, scoreset_urn, dataset_columns,
                    base_url=""):
    """Bulk creates and emails the user the processing status."""
    # Bind task instance variables
    self.urn = scoreset_urn
    self.base_url = base_url
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


