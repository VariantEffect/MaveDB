import dataset.constants as constants

def is_null(value):
    return str(value).strip().lower() in constants.nan_col_values