import numpy as np
import pandas as pd
from pandas.testing import assert_index_equal

from core.utilities import is_null


def convert_df_to_variant_records(scores, counts=None, index=None):
    """
    Given two `defaultdict`s `score_map` and `count_map`, create an
    `OrderedDict` indexed by `hgvs_nt` where the keys are the attribute
    fields required to instantiate a `variant.models.Variant` instance.

    NOTE: Assumes that the dataframes are indexed by their primary columns,
    and that they define the same variants in both hgvs columns.

    Parameters
    ----------
    scores : Union[`pd.DataFrame`, str]
        Map indexed by the primary hgvs column inferred during validation.
        Map values are `dict` records where the key-pairs are column-value
        pairs inferred from the `scores` file uploaded during submission.
    counts : Union[`pd.DataFrame`, str] optional
        Map indexed by the primary hgvs column inferred during validation.
        Map values are `dict` records where the key-pairs are column-value
        pairs inferred from the `counts` file uploaded during submission.
    index : str
        Column to use as index, which is used when grouping rows between
        dataframes.

    Returns
    -------
    `list`
        Formatted records that can be used to create `variant.models.Variant`
        instances.
    """
    from dataset.validators import validate_datasets_define_same_variants
    from dataset.constants import (
        hgvs_nt_column,
        hgvs_pro_column,
        hgvs_splice_column,
        variant_count_data,
        variant_score_data,
    )

    if isinstance(scores, str):
        scores = pd.read_json(scores, orient="records")
    if isinstance(counts, str):
        counts = pd.read_json(counts, orient="records")

    has_count_data = counts is not None and len(counts) > 0
    has_score_data = scores is not None and len(scores) > 0

    if index:
        scores.index = pd.Index(scores[index])
        if has_count_data:
            counts.index = pd.Index(counts[index])

    if not has_score_data:
        return []

    if has_count_data:
        assert_index_equal(
            scores.index.sort_values(), counts.index.sort_values()
        )
        validate_datasets_define_same_variants(scores, counts)

    variants = []
    for (primary_hgvs, group) in scores.groupby(by=scores.index, sort=False):
        score_records = group.to_dict(orient="records")
        if has_count_data:
            count_records = counts[counts.index == primary_hgvs].to_dict(
                orient="records"
            )
            assert len(score_records) == len(count_records)
        else:
            # Make duplicates to zip with self when no count data.
            count_records = [r.copy() for r in score_records]

        for (sr, cr) in zip(score_records, count_records):
            hgvs_nt = sr.pop(hgvs_nt_column)
            hgvs_splice = sr.pop(hgvs_splice_column)
            hgvs_pro = sr.pop(hgvs_pro_column)

            if is_null(hgvs_nt) or hgvs_nt is np.NaN or hgvs_nt == "nan":
                hgvs_nt = None
            if (
                is_null(hgvs_splice)
                or hgvs_splice is np.NaN
                or hgvs_splice == "nan"
            ):
                hgvs_splice = None
            if is_null(hgvs_pro) or hgvs_pro is np.NaN or hgvs_pro == "nan":
                hgvs_pro = None

            cr.pop(hgvs_nt_column)
            cr.pop(hgvs_splice_column)
            cr.pop(hgvs_pro_column)

            # Postgres JSON field cannot store np.NaN values so convert
            # any np.NaN to None.
            for key, value in sr.items():
                if is_null(value) or value is np.NaN:
                    sr[key] = None
            if cr:
                for key, value in cr.items():
                    if is_null(value) or value is np.NaN:
                        cr[key] = None

            data = {
                variant_score_data: sr,
                variant_count_data: {} if cr == sr else cr,
            }
            variant = {
                hgvs_nt_column: hgvs_nt,
                hgvs_splice_column: hgvs_splice,
                hgvs_pro_column: hgvs_pro,
                "data": data,
            }
            variants.append(variant)

    return variants
