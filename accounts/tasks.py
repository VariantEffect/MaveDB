from celery.utils.log import get_task_logger

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.contrib.auth import get_user_model

from core.tasks import LogErrorsTask
from mavedb import celery_app

from dataset import models

from urn.models import get_model_by_urn


logger = get_task_logger('accounts.tasks')
User = get_user_model()


@celery_app.task(ignore_result=True, base=LogErrorsTask)
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


@celery_app.task(ignore_result=True, base=LogErrorsTask)
def notify_user_group_change(base_url, user, urn, action, group):
    if not isinstance(user, User):
        user = User.objects.get(pk=user)
    instance = get_model_by_urn(urn)
    
    if isinstance(instance, models.experiment.Experiment):
        path = reverse("dataset:experiment_detail", args=(instance.urn,))
    elif isinstance(instance, models.scoreset.ScoreSet):
        path = reverse("dataset:scoreset_detail", args=(instance.urn,))
    elif isinstance(instance, models.experimentset.ExperimentSet):
        path = reverse("dataset:experimentset_detail", args=(instance.urn,))
    else:
        logger.error(
            "{} passed to accounts.utlitiles.notify_user_group_change "
            "is not a valid viewable instance.".format(type(instance).__name__)
        )
        return

    if isinstance(base_url, dict):
        base_url = base_url['BASE_URL']
    if isinstance(base_url, str):
        absolute_url = base_url + path
    else:
        logger.error("Unkown base_url type '{}'".format(
            type(base_url).__name__))
        return

    email = user.profile.email or user.email
    if action == 'removed':
        conjunction = 'from'
    else:
        conjunction = 'for'

    if group in ('administrator', 'editor'):
        group = 'an {}'.format(group)
    else:
        group = 'a {}'.format(group)

    if email:
        template_name = "accounts/added_removed_as_contributor.html"
        message = render_to_string(template_name, {
            'user': user, 'group': group, 'conjunction': conjunction,
            'url': absolute_url, 'action': action, 'urn': instance.urn
        })
        send_mail(
            subject='Updates to entry {}.'.format(instance.urn),
            message=message,
            from_email=None,
            recipient_list=[email]
        )
    else:
        logger.error(
            "Tried to notify user '{}' from accounts.utilities.notify_"
            "user_group_change but could not find an email "
            "address.".format(user.username)
        )


@celery_app.task(ignore_result=True, base=LogErrorsTask)
def email_user(user, **kwargs):
    if isinstance(user, int):
        if User.objects.filter(pk=user).count():
            user = User.objects.get(pk=user)
    if isinstance(user, User):
        user.profile.email_user(**kwargs)
