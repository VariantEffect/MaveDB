import sys
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta

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


def run_delayed_task(task, *args, **kwargs):
    """
    Windows has touble running Celery tasks due to dropped support. This should
    be used during development on windows platforms.
    """
    if sys.platform == 'win32':
        return task(*args, **kwargs)
    else:
        return task.delay(*args, **kwargs)
