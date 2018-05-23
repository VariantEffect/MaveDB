import logging

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.urls import reverse
from django.core.mail import send_mail

from urn.models import get_model_by_urn
from dataset import models
from mavedb import celery_app

User = get_user_model()
logger = logging.getLogger("django")


@celery_app.task(ignore_result=True)
def email_user(user, **kwargs):
    if isinstance(user, int):
        if User.objects.filter(pk=user).count():
            user = User.objects.get(pk=user)
        else:
            return False
    return user.profile.email_user(**kwargs)


@celery_app.task(ignore_result=True)
def send_to_email(subject, message, from_email, recipient_list, **kwargs):
    if recipient_list:
        return send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            **kwargs
        )
    return False
    

@celery_app.task(ignore_result=True)
def email_admins(user, urn, base_url=""):
    """
    Sends an email to all admins.

    Parameters
    ----------
    user : `auth.User`
        The user who created the instance.
    urn : `str`
        URN of the instance created.
    base_url : `str`
        Host domain name
    """
    logger.warning("Entered delay call")
    if isinstance(user, int):
        user = User.objects.get(pk=user)
    instance = get_model_by_urn(urn)

    url = base_url
    if isinstance(instance, models.scoreset.ScoreSet):
        url += reverse('dataset:scoreset_detail', args=(instance.urn,))
    elif isinstance(instance, models.experiment.Experiment):
        url += reverse('dataset:experiment_detail', args=(instance.urn,))
    elif isinstance(instance, models.experimentset.ExperimentSet):
        url += reverse('dataset:experimentset_detail', args=(instance.urn,))
    else:
        raise TypeError("Cannot find url for type {}.".format(type(instance)))

    template_name = "core/alert_admin_new_entry_email.html"
    admins = User.objects.filter(is_superuser=True)
    message = render_to_string(template_name, {
        'user': user,
        'url': url,
        'class_name': type(instance).__name__,
    })

    subject = "[MAVEDB ADMIN] New entry requires your attention."
    for admin in admins:
        logger.info("Sending email to {}".format(admin.username))
        admin.email_user(subject, message)
