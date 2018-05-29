from celery.task import Task
from celery.utils.log import get_task_logger

from django.template.loader import render_to_string
from django.db import transaction
from django.contrib.auth import get_user_model

from core.tasks import email_admins

from mavedb import celery_app

from variant.models import Variant

from dataset import constants
from .models.scoreset import ScoreSet


logger = get_task_logger(__name__)
User = get_user_model()


def _get_task_context(kwargs):
    scoreset_urn = kwargs['scoreset_urn']
    user_pk = kwargs['user_pk']
    base_url = kwargs.get('base_url', "")
    user = User.objects.get(pk=user_pk)
    if ScoreSet.objects.filter(urn=scoreset_urn).count():
        scoreset = ScoreSet.objects.get(urn=scoreset_urn)
    else:
        scoreset = None
    return scoreset, scoreset_urn, user, base_url


def _task_fail_callback(task, exc, task_id, args, kwargs, einfo):
    scoreset, urn, user, base_url = _get_task_context(kwargs)
    if scoreset:
        scoreset.processing_state = constants.failed
        scoreset.save()
    
    logger.exception(
        "CELERY: Task (name={}, id={}) raised exception while saving "
        "variants to ScoreSet {} from user {}:\n{!r}\n{!r}.".format(
            task.name, task_id, urn, user.username, str(exc), einfo)
    )
    notify_user_upload_status.delay(
        user_pk=user.pk, scoreset_urn=urn,
        success=False, base_url=base_url)


class BaseCreateVariants(Task):
    """Adds in error handling callback when a task fails"""
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        _task_fail_callback(self, exc, task_id, args, kwargs, einfo)
        return super(BaseCreateVariants, self).on_failure(
            exc, task_id, args, kwargs, einfo)
    
    def on_success(self, retval, task_id, args, kwargs):
        scoreset, urn, user, base_url = _get_task_context(kwargs)
        if scoreset:
            scoreset.processing_state = constants.success
            scoreset.save()
            
        notify_user_upload_status.delay(
            user_pk=user.pk, scoreset_urn=urn,
            base_url=base_url, success=True
        )
        
        return super(BaseCreateVariants, self).on_success(
            retval, task_id, args, kwargs)


class BasePublish(Task):
    """Adds in error handling callback when a task fails"""
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        _task_fail_callback(self, exc, task_id, args, kwargs, einfo)
        return super(BasePublish, self).on_failure(
            exc, task_id, args, kwargs, einfo)
    
    def on_success(self, retval, task_id, args, kwargs):
        scoreset, urn, user, base_url = _get_task_context(kwargs)
        if scoreset:
            scoreset.processing_state = constants.failed
            scoreset.save()
        
        notify_user_upload_status.delay(
            user_pk=user.pk, scoreset_urn=urn,
            base_url=base_url, success=True
        )
        email_admins.delay(
            user=user.pk,
            urn=scoreset.urn,
            base_url=base_url
        )
        return super(BasePublish, self).on_success(
            retval, task_id, args, kwargs)
    

# Note: don't remove unused arguments for the tasks below. They are required
# for the on_failure and on_success callbacks.
@celery_app.task(ignore_result=True, base=BasePublish)
def publish_scoreset(user_pk, scoreset_urn, base_url=""):
    user = User.objects.get(pk=user_pk)
    scoreset = ScoreSet.objects.get(urn=scoreset_urn)
    scoreset.publish()
    scoreset.set_modified_by(user, propagate=True)
    scoreset.processing_state = constants.success
    scoreset.save(save_parents=True)
    scoreset.refresh_from_db()
    return scoreset


@celery_app.task(ignore_result=True, base=BaseCreateVariants)
def create_variants(user_pk, variants, scoreset_urn, dataset_columns, base_url=""):
    """Bulk creates and emails the user the processing status."""
    scoreset = ScoreSet.objects.get(urn=scoreset_urn)
    with transaction.atomic():
        scoreset.delete_variants()
        Variant.bulk_create(scoreset, [v for _, v in variants.items()])
        scoreset.dataset_columns = dataset_columns
        scoreset.processing_state = constants.success
        scoreset.save()
    scoreset.processing_state = constants.success
    scoreset.save()


@celery_app.task(ignore_result=True)
def notify_user_upload_status(user_pk, scoreset_urn, success, base_url=""):
    user = User.objects.get(pk=user_pk)
    if success:
        template_name = "accounts/celery_complete_email_success.html"
    else:
        template_name = "accounts/celery_complete_email_failed.html"
    subject = "Your submission has been processed."
    message = render_to_string(template_name, {
        'urn': scoreset_urn, 'user': user, 'base_url': base_url
    })
    user.profile.email_user(subject=subject, message=message)
