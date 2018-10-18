from django.db import transaction
from django.contrib.auth import get_user_model
from django.conf import settings

from celery.utils.log import get_task_logger

from core.utilities import notify_admins
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
SOFT_TIME_LIMIT = settings.DATASET_TASK_SOFT_TIME_LIMIT


class BaseDatasetTask(BaseTask):
    """
    Edits the scoreset processing state and emails user.
    Delegates task logging and saving to BaseTask.
    """
    def on_failure(self, exc, task_id, args, kwargs, einfo, user=None):
        if isinstance(self.scoreset, models.scoreset.ScoreSet):
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


class BaseDelete(BaseDatasetTask):
    """Adds in error handling callback when a task succeeds/fails"""
    def on_failure(self, exc, task_id, args, kwargs, einfo, user=None):
        if self.instance is not None:
            # Reset to success and not fail. Setting to fail will
            # prevent other actions.
            self.instance.refresh_from_db()
            self.instance.processing_state = constants.success
            self.instance.save()
        if isinstance(self.user, User):
            self.user.profile.notify_user_delete_status(
                success=False, urn=self.urn,
            )
        return super(BaseDatasetTask, self).on_failure(
            exc, task_id, args, kwargs, einfo, user=self.user)

    def on_success(self, retval, task_id, args, kwargs):
        self.user.profile.notify_user_delete_status(
            success=True, urn=self.urn,
        )
        return super(BaseDelete, self).on_success(
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
    self.scoreset = models.scoreset.ScoreSet.objects.get(urn=self.urn)
    with transaction.atomic():
        self.scoreset = publish_dataset(dataset=self.scoreset, user=self.user)
        self.urn = self.scoreset.urn
    return self.scoreset


@celery_app.task(bind=True, ignore_result=True,
                 base=BaseDelete, soft_time_limit=SOFT_TIME_LIMIT)
def delete_instance(self, user_pk, urn):
    # Bind task instance variables
    self.urn = urn
    self.instance = None
    self.user = None
    # Look for instances. This might throw an ObjectDoesNotExist exception.
    # Bind ORM objects if they were found
    user = User.objects.get(pk=user_pk)
    self.user = user
    self.instance = get_model_by_urn(self.urn)
    if self.instance.children.count() and \
            not isinstance(self.instance, models.scoreset.ScoreSet):
        raise ValueError("{} has children and cannot be deleted.".format(
            self.urn))
    with transaction.atomic():
        return delete_instance_util(self.instance)


@celery_app.task(bind=True, ignore_result=True,
                 base=BaseCreateVariants, soft_time_limit=SOFT_TIME_LIMIT)
def create_variants(self, user_pk, scoreset_urn, scores_df, counts_df,
                    dataset_columns):
    """Bulk creates and emails the user the processing status."""
    # Bind task instance variables
    self.urn = scoreset_urn
    self.scoreset = None
    self.user = None

    # Look for instances. This might throw an ObjectDoesNotExist exception.
    # Bind ORM objects if they were found
    user = User.objects.get(pk=user_pk)
    self.user = user
    scoreset = models.scoreset.ScoreSet.objects.get(urn=scoreset_urn)
    self.scoreset = scoreset
    variants = convert_df_to_variant_records(scores_df, counts_df)
    with transaction.atomic():
        scoreset.delete_variants()
        Variant.bulk_create(scoreset, variants)
        scoreset.dataset_columns = dataset_columns
        scoreset.save()
    return scoreset

