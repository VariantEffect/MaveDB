
"""
Module contains some helper/utility functions to parse search queries.
"""

import re


def enclosed_by_quotes(s):
    """
    Checks if a string is enclosed by double or single quotes.

    Parameters
    ----------
    s : `str`
        The string to check

    Returns
    -------
    `bool`
        True if surrounded by quotes, false otherwise.
    """
    return (s.startswith("'") and s.endswith("'")) or \
        (s.startswith('"') and s.endswith('"'))


def parse_query(query, sep=','):
    """
    Parse a search field query into separate queries according to a comma
    delimiter by default

    Parameters
    ----------
    query : `str`
        The search string recieved from a search field.
    sep : `str`, default ','
        The separator we should use to separate individual queries.

    Returns
    -------
    `list`
        A list of separate queries.
    """
    pattern = r"(['\"]([^'\"]*)['\"])".format(sep)
    queries = [q.strip() for q in re.split(pattern, query) if q.strip()]
    parsed = []
    index = 0
    while index < len(queries):
        query = queries[index]
        if enclosed_by_quotes(query):
            parsed.append(query[1:-1])
            index += 2
        else:
            simple_queries = [q.strip() for q in query.split(sep) if q.strip()]
            parsed.extend(simple_queries)
            index += 1
    return [q.strip() for q in parsed if q.strip()]
