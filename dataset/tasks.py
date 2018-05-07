import logging

from celery.task import Task

from django.template.loader import render_to_string
from django.db import transaction
from django.contrib.auth import get_user_model

from core.tasks import send_admin_email

from mavedb import celery_app

from variant.models import Variant

from dataset import constants
from .models.scoreset import ScoreSet


logger = logging.getLogger('django')
User = get_user_model()


class BaseCreateVariants(Task):
    """Adds in error handling callback when a task fails"""
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        scoreset_urn = kwargs['scoreset_urn']
        user_pk = kwargs['user_pk']
        base_url = kwargs.get('base_url', "")
        user = User.objects.get(pk=user_pk)
        scoreset = ScoreSet.objects.get(urn=scoreset_urn)
        scoreset.processing_state = constants.failed
        scoreset.save()
        notify_user_upload_status.delay(
            user_pk=user_pk, scoreset_urn=scoreset_urn,
            step='end', base_url=base_url)
        logger.exception(
            "CELERY: Task {} raised exception while saving "
            "variants to ScoreSet {} from user {}:\n{!r}\n{!r}.".format(
                task_id, scoreset.urn, user.username, str(exc), einfo)
        )
        return super(BaseCreateVariants, self).on_failure(
            exc, task_id, args, kwargs, einfo)


@celery_app.task(ignore_result=True)
def publish_scoreset(scoreset_urn, user_pk, base_url):
    user = User.objects.get(pk=user_pk)
    scoreset = ScoreSet.objects.get(urn=scoreset_urn)
    scoreset.set_modified_by(user, propagate=True)
    scoreset.publish(propagate=True)
    scoreset.save(save_parents=True)
    send_admin_email.delay(user=user.pk, urn=scoreset.urn, base_url=base_url)


@celery_app.task(ignore_result=True, base=BaseCreateVariants)
def create_variants(user_pk, variants, scoreset_urn, dataset_columns,
                    publish=False, base_url=""):
    """Bulk creates and emails the user the processing status."""
    scoreset = ScoreSet.objects.get(urn=scoreset_urn)
    notify_user_upload_status.delay(
        user_pk=user_pk, scoreset_urn=scoreset_urn,
        step='start', base_url=base_url)
    with transaction.atomic():
        scoreset.delete_variants()
        Variant.bulk_create(scoreset, [v for _, v in variants.items()])
        scoreset.dataset_columns = dataset_columns
        scoreset.processing_state = constants.success
        scoreset.save()
        notify_user_upload_status.delay(
            user_pk=user_pk, scoreset_urn=scoreset_urn,
            step='end', base_url=base_url)
        if publish:
            publish_scoreset.delay(
                scoreset_urn=scoreset_urn, user_pk=user_pk, base_url=base_url)


@celery_app.task(ignore_result=True)
def notify_user_upload_status(user_pk, scoreset_urn,
                              step="start", base_url=""):
    user = User.objects.get(pk=user_pk)
    if step == 'start':
        template_name = "accounts/celery_start_email.html"
        subject = "Your submission is being processed."
        message = render_to_string(template_name, {
            'urn': scoreset_urn, 'user': user, 'base_url': base_url,
        })
    else:
        template_name = "accounts/celery_complete_email.html"
        subject = "Your submission has been processed."
        message = render_to_string(template_name, {
            'urn': scoreset_urn, 'user': user, 'base_url': base_url,
        })

    user.profile.email_user(
        subject=subject,
        message=message
    )
