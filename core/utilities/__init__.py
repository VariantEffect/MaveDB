import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta

from django.contrib.auth.models import User
from django.template.loader import render_to_string

import dataset.constants as constants


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


def send_admin_email(user, instance):
    """
    Sends an email to all admins.

    Parameters
    ----------
    user : `auth.User`
        The user who created the instance.
    instance : `object`
        The instance created.

    """
    template_name = "core/alert_admin_new_entry_email.html"
    admins = User.objects.filter(is_superuser=True)
    message = render_to_string(template_name, {
        'user': user,
        'instance': instance,
        'class_name': instance.__class__.__name__
    })

    subject = "[MAVEDB ADMIN] New entry requires your attention."
    for admin in admins:
        logger.info("Sending email to {}".format(admin.username))
        admin.email_user(subject, message)
