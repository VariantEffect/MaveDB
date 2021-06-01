"""
Constant definitions for application `experiment`.
"""
from urn.validators import (
    MAVEDB_EXPERIMENTSET_URN_PATTERN,
    MAVEDB_EXPERIMENT_URN_PATTERN,
    MAVEDB_SCORESET_URN_PATTERN,
    MAVEDB_TMP_URN_PATTERN,
)


hgvs_nt_column = "hgvs_nt"
hgvs_splice_column = "hgvs_splice"
hgvs_pro_column = "hgvs_pro"
hgvs_columns = sorted([hgvs_nt_column, hgvs_pro_column, hgvs_splice_column])
meta_data = "meta_data"
score_columns = "score_columns"
count_columns = "count_columns"
variant_score_data = "score_data"
variant_count_data = "count_data"
required_score_column = "score"

experimentset_url_pattern = "|".join(
    [MAVEDB_EXPERIMENTSET_URN_PATTERN[1:-1], MAVEDB_TMP_URN_PATTERN[1:-1]]
)
experiment_url_pattern = "|".join(
    [MAVEDB_EXPERIMENT_URN_PATTERN[1:-1], MAVEDB_TMP_URN_PATTERN[1:-1]]
)
scoreset_url_pattern = "|".join(
    [MAVEDB_SCORESET_URN_PATTERN[1:-1], MAVEDB_TMP_URN_PATTERN[1:-1]]
)

any_url_pattern = "|".join(
    [experimentset_url_pattern, experiment_url_pattern, scoreset_url_pattern]
)


valid_dataset_columns = [score_columns, count_columns]
valid_variant_columns = [variant_score_data, variant_count_data]

variant_to_scoreset_column = {
    variant_score_data: score_columns,
    variant_count_data: count_columns,
}
scoreset_to_variant_column = {
    v: k for k, v in variant_to_scoreset_column.items()
}

# Celery dataset status
processing = "processing"
failed = "failed"
success = "success"

# User roles
administrator = "administrator"
editor = "editor"
viewer = "viewer"
