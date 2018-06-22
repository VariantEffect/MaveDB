import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.shortcuts import reverse
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model

from dataset import constants
from dataset import models


User = get_user_model()
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


def notify_admins(user, instance):
    """
    Sends an email to all admins.

    Parameters
    ----------
    user : `User`
        The user who published the instance.
    instance : `DatasetModel`
        instance that was published
    """
    from main.context_processors import baseurl

    url = baseurl(request=None)['base_url']

    if isinstance(instance, models.scoreset.ScoreSet):
        url += reverse('dataset:scoreset_detail', args=(instance.urn,))
    elif isinstance(instance, models.experiment.Experiment):
        url += reverse('dataset:experiment_detail', args=(instance.urn,))
    elif isinstance(instance, models.experimentset.ExperimentSet):
        url += reverse('dataset:experimentset_detail', args=(instance.urn,))
    else:
        raise TypeError("{} does not have a reverse url".format(
            type(instance).__name__
        ))

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
        admin.profile.email_user(subject=subject, message=message)


def base_url(request=None):
    if request is None:
        scheme = 'http://'
    else:
        if request.is_secure():
            scheme = 'https://'
        else:
            scheme = 'http://'
    return scheme + settings.BASE_URL
