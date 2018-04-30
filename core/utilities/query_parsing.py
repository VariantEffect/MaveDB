
"""
Module contains some helper/utility functions to parse search queries.
"""

import csv

from . import is_null


def filter_empty(ls):
    """
    Filter a list only returning non-false values.

    Parameters
    ----------
    ls: `list`
        List to filter

    Returns
    -------
    `list`
        Filtered list
    """
    return [x for x in ls if not is_null(x)]


def parse_query(query):
    """
    Parse a search field query into separate queries according to a comma
    delimiter by default

    Parameters
    ----------
    query : `str`
        The search string recieved from a search field.

    Returns
    -------
    `list`
        A list of separate queries.
    """
    if not isinstance(query, list):
        query = [query]
    return filter_empty(list(csv.reader(query)))
