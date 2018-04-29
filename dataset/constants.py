"""
Constant definitions for application `experiment`.
"""

from urn.validators import (
    MAVEDB_EXPERIMENTSET_URN_PATTERN,
    MAVEDB_EXPERIMENT_URN_PATTERN,
    MAVEDB_SCORESET_URN_PATTERN
)

nan_col_values = {
    '', ' ',
    'nan', 'na', 'none', 'null',
    'NaN', 'None', 'Na', 'NA', 'NULL'
}
hgvs_column = "hgvs"
score_columns = "score_columns"
count_columns = "count_columns"
meta_columns = "meta_columns"
variant_score_data = 'score_data'
variant_count_data = 'count_data'
variant_meta_data = 'meta_data'
required_score_column = 'score'

experimentset_url_pattern = MAVEDB_EXPERIMENTSET_URN_PATTERN[1:-1]
experiment_url_pattern = MAVEDB_EXPERIMENT_URN_PATTERN[1:-1]
scoreset_url_pattern = MAVEDB_SCORESET_URN_PATTERN[1:-1]
any_url_pattern = '|'.join([
    experimentset_url_pattern, experiment_url_pattern, scoreset_url_pattern
])


valid_dataset_columns = [
    score_columns,
    count_columns,
    meta_columns
]
valid_variant_columns = [
    variant_score_data,
    variant_count_data,
    variant_meta_data
]

variant_to_scoreset_column = {
    variant_score_data: score_columns,
    variant_count_data: count_columns,
    variant_meta_data: meta_columns
}
scoreset_to_variant_column = {
    v: k for k, v in variant_to_scoreset_column.items()
}