import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta

from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.shortcuts import reverse

from mavedb import celery_app

import dataset.constants as constants
from dataset import models

logger = logging.getLogger("django")


def is_null(value):
    """Returns True if a stripped/lowercase value in in `nan_col_values`."""
    return str(value).strip().lower() in constants.nan_col_values


def format_delta(ta, tb=None):
    if tb is None:
        tb = datetime.now()

    t_diff = relativedelta(tb, ta)
    if t_diff.years:
        units = "years"
    elif t_diff.months:
        units = "months"
    elif t_diff.weeks:
        units = "weeks"
    else:
        units = "days"

    delta = getattr(t_diff, units)
    if delta == 0:
        return "today"
    elif delta == 1:
        return "{} {} ago".format(delta, units[:-1])
    else:
        return "{} {} ago".format(delta, units)


@celery_app.task(ignore_result=True)
def send_admin_email(user, urn, base_url=""):
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
    if isinstance(user, int):
        user = User.objects.get(pk=user)
    instance = models.get_model_by_urn(urn)

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
