import re
import logging
from datetime import datetime

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.shortcuts import reverse
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model


User = get_user_model()
logger = logging.getLogger("django")

# Used in CSV formatting
NA_value = "NA"

null_values_list = (
    "nan",
    "na",
    "none",
    "",
    "undefined",
    "n/a",
    "null",
    "nil",
    NA_value,
)
null_values_re = re.compile(
    # ^\s+$ means the string is all whitespace. "start and end with space" implies that something like " 123 " would also count
    r"^\s+$|none|nan|na|undefined|n/a|null|nil|{}".format(NA_value),
    flags=re.IGNORECASE,
)
readable_null_values = [
    "'{}'".format(v)
    for v in set([v.lower() for v in null_values_list])
    if v.strip()
] + ["whitespace"]

html_null_values = [
    f"<b>{v.strip().lower() or 'whitespace'}</b>" for v in null_values_list
]
humanized_null_values = (
    f'{", ".join(html_null_values[:-1])} ' f"and " f"{html_null_values[-1]}"
)


def is_null(value):
    """Returns True if a stripped/lowercase value in in `nan_col_values`."""
    value = str(value).strip().lower()
    return null_values_re.fullmatch(value) or not value


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
    from dataset import models
    from main.context_processors import baseurl

    url = baseurl(request=None)["base_url"]

    if isinstance(instance, models.scoreset.ScoreSet):
        url += reverse("dataset:scoreset_detail", args=(instance.urn,))
    elif isinstance(instance, models.experiment.Experiment):
        url += reverse("dataset:experiment_detail", args=(instance.urn,))
    elif isinstance(instance, models.experimentset.ExperimentSet):
        url += reverse("dataset:experimentset_detail", args=(instance.urn,))
    else:
        raise TypeError(
            "{} does not have a reverse url".format(type(instance).__name__)
        )

    template_name = "core/alert_admin_new_entry_email.html"
    admins = User.objects.filter(is_superuser=True)
    message = render_to_string(
        template_name,
        {"user": user, "url": url, "class_name": type(instance).__name__},
    )

    subject = "[MAVEDB ADMIN] New entry requires your attention."
    for admin in admins:
        logger.info("Sending email to {}".format(admin.username))
        admin.profile.email_user(subject=subject, message=message)


def base_url(request=None):
    if request is None:
        scheme = "http://"
    else:
        if request.is_secure():
            scheme = "https://"
        else:
            scheme = "http://"
    return scheme + settings.BASE_URL


def format_column(values, astype=float):
    """
    Formats a list of numeric values by replacing null values with
    `np.NaN` and casting to `astype`.

    Parameters
    ----------
    values : `pd.Series`
        List of values to format.

    astype : callable, optional
        Type-casting callback accepting a single argument.

    Returns
    -------
    list[Any]
        List of values with type returned by `astype` and null values
        replaced with `np.NaN`.
    """
    if astype == str:
        nan_val = None
    else:
        nan_val = np.NaN
    return [nan_val if is_null(v) else astype(v) for v in values]


def chunks(ls, n):
    """Return elements in a list, n at a time."""
    for i in range(0, len(ls), n):
        yield ls[i : i + n]
