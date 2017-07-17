
"""
Module contains some helper/utility functions to parse search queries.
"""


def chain_until_next_quotes(items, sep=','):
    """
    Looks at a list of strings that have been split by `sep`
    and tries to collect items in the list that start with '"' and end
    with '"' into a single string.

    Parameters
    ----------
    items : `list`
        List of strings
    sep : `str`
        Separator used to split the list of strings.

    Returns
    -------
    `tuple`
        The resulting joined string and the number of items joined.
    """
    i = 1
    string = items[0]
    state = 'open'

    if not string.startswith('"') and not string.startswith("'"):
        return string.strip(), i
    else:
        while i < len(items):
            item = items[i]
            string = '{}{}{}'.format(string, sep, item)
            i += 1
            if string.startswith('"') and item.endswith('"'):
                break
            if string.startswith("'") and item.endswith("'"):
                break
        return string.strip()[1:-1], i


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
    queries = query.split(sep)
    parsed = []
    i = 0
    while i < len(queries):
        query, items_taken = chain_until_next_quotes(queries[i:])
        i += items_taken
        parsed.append(query)
    return [q.strip() for q in parsed if q.strip()]
