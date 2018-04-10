import dataset.constants as constants

def is_null(value):
    """Returns True if a stripped/lowercase value in in `nan_col_values`."""
    return str(value).strip().lower() in constants.nan_col_values