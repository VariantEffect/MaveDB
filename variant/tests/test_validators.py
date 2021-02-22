from io import BytesIO, StringIO

import pandas as pd
from django.core.exceptions import ValidationError
from django.test import TestCase
from pandas.testing import assert_index_equal, assert_frame_equal

from core.utilities import null_values_list
from dataset import constants

from ..factories import generate_hgvs, VariantFactory
from ..validators import (
    MaveDataset,
    validate_columns_match,
    validate_variant_json,
    validate_hgvs_string,
)


class TestValidateMatchingColumns(TestCase):
    """
    Tests the function :func:`validate_scoreset_columns_match_variant` which
    throws a `ValidationError` if the keys of a variant's data do not match
    the corresponding columns defined in the parent
    :class:`dataset.models.scoreset.ScoreSet`.
    """

    def test_validation_error_non_matching_score_columns(self):
        variant = VariantFactory()
        with self.assertRaises(ValidationError):
            variant.data[constants.variant_score_data] = {}
            validate_columns_match(variant, variant.scoreset)

    def test_validation_error_non_matching_count_columns(self):
        variant = VariantFactory()
        with self.assertRaises(ValidationError):
            variant.data[constants.variant_count_data] = {"count": 1}
            validate_columns_match(variant, variant.scoreset)

    def test_compares_sorted_columns(self):
        variant = VariantFactory()
        variant.data[constants.variant_score_data] = {
            "other": 1,
            constants.required_score_column: 1,
        }
        variant.scoreset.dataset_columns[constants.score_columns] = [
            constants.required_score_column,
            "other",
        ]
        # This should pass
        validate_columns_match(variant, variant.scoreset)


class TestHGVSValidator(TestCase):
    """
    Tests the function :func:`validate_hgvs_string` to see if it is able
    to validate strings which do not comply with the HGVS standard for
    coding, non-coding and nucleotide variants and multi-variants.
    """

    def test_validation_error_not_str_or_bytes(self):
        with self.assertRaises(ValidationError):
            validate_hgvs_string([])

    def test_does_not_pass_enrich_wt_hgvs(self):
        with self.assertRaises(ValidationError):
            validate_hgvs_string("_wt")

    def test_does_not_pass_enrich_sy_hgvs(self):
        with self.assertRaises(ValidationError):
            validate_hgvs_string("_sy")

    def test_passes_multi(self):
        validate_hgvs_string("p.[Lys4Gly;Lys5Phe]", column="p")
        validate_hgvs_string("c.[1A>G;127_128delinsAGC]", column="nt")
        validate_hgvs_string("c.[1A>G;127_128delinsAGC]", column="splice")

    def test_error_invalid_hgvs(self):
        with self.assertRaises(ValidationError):
            validate_hgvs_string("c.ad", column="nt")

    def test_error_invalid_nt_prefix(self):
        with self.assertRaises(ValidationError):
            validate_hgvs_string("r.1a>g", column="nt")

        with self.assertRaises(ValidationError):
            validate_hgvs_string("c.1A>G", column="nt", splice_present=True)

    def test_error_invalid_splice_prefix(self):
        with self.assertRaises(ValidationError):
            validate_hgvs_string("r.1a>g", column="splice")

    def test_error_invalid_pro_prefix(self):
        with self.assertRaises(ValidationError):
            validate_hgvs_string("r.1a>g", column="p")

    def test_converts_bytes_to_string_before_validation(self):
        validate_hgvs_string(b"c.427A>G", column="splice")

    def test_return_none_for_null(self):
        for c in null_values_list:
            self.assertIsNone(validate_hgvs_string(c, column="nt"))


class TestVariantJsonValidator(TestCase):
    """
    Tests the validator :func:`validate_variant_json` to check if the correct
    errors are thrown if an incorrectly formatted `dictionary` is set
    as a the `data` `JSONField` attribute of a :class:`..models.Variant`
    instance.
    """

    def test_validation_error_missing_score_data_key(self):
        data = {constants.variant_count_data: {}}
        with self.assertRaises(ValidationError):
            validate_variant_json(data)

    def test_validation_error_missing_count_data_key(self):
        data = {constants.variant_score_data: {}}
        with self.assertRaises(ValidationError):
            validate_variant_json(data)

    def test_validation_error_contains_unexpected_keys(self):
        data = {
            "extra": {},
            constants.variant_score_data: {},
            constants.variant_count_data: {},
        }
        with self.assertRaises(ValidationError):
            validate_variant_json(data)

    def test_validation_error_values_not_dict(self):
        data = {
            constants.variant_score_data: {},
            constants.variant_count_data: {},
        }
        for key in data.keys():
            data[key] = []
            with self.assertRaises(ValidationError):
                validate_variant_json(data)
            data[key] = {}


class TestMaveDataset(TestCase):
    """
    Tests the validator :func:`validate_variant_rows` to check if the correct
    errors are thrown when invalid rows are encountered in a
    scores/counts/meta data input file. Checks for:
        - Invalid HGVS string in a row
        - Row HGVS is defined in more than one row
        - Row values are not int/float for a count/score file

    Tests also check to see if the correct header and hgvs data information
    is parsed and returned.
    """

    SCORE_COL = constants.required_score_column
    HGVS_NT_COL = constants.hgvs_nt_column
    HGVS_SPLICE_COL = constants.hgvs_splice_column
    HGVS_PRO_COL = constants.hgvs_pro_column

    @staticmethod
    def mock_return_value(data, index=None):
        df = pd.read_csv(StringIO(data), sep=",", na_values=["None", None])
        if index:
            df.index = pd.Index(df[index])
        return df

    def test_invalid_row_hgvs_is_not_a_string(self):
        data = "{},{}\n1.0,1.0".format(self.HGVS_NT_COL, self.SCORE_COL)

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertFalse(dataset.is_valid)
        self.assertEqual(len(dataset.errors), 1)
        print(dataset.errors)

    def test_invalid_missing_hgvs_columns(self):
        data = "{},{}\n{},1.0".format(
            "not_hgvs", self.SCORE_COL, generate_hgvs()
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertFalse(dataset.is_valid)
        self.assertEqual(len(dataset.errors), 1)
        print(dataset.errors)

    def test_replaces_null_with_none_in_secondary_hgvs_column(self):
        hgvs_nt = generate_hgvs(prefix="c")
        for c in null_values_list:
            with self.subTest(msg=f"'{c}'"):
                data = "{},{},{}\n{},{},1.0 ".format(
                    self.HGVS_NT_COL,
                    self.HGVS_PRO_COL,
                    self.SCORE_COL,
                    hgvs_nt,
                    c,
                )

                dataset = MaveDataset.for_scores(StringIO(data))
                dataset.validate()

                self.assertTrue(dataset.is_valid)
                self.assertListEqual(
                    list(dataset.data(serializable=True)[self.HGVS_PRO_COL]),
                    [None],
                )

    def test_replaces_null_with_none_in_numeric_columns(self):
        hgvs_nt = generate_hgvs(prefix="c")
        for c in null_values_list:
            with self.subTest(msg=f"'{c}'"):
                data = "{},{}\n{},{}".format(
                    self.HGVS_NT_COL,
                    self.SCORE_COL,
                    hgvs_nt,
                    c,
                )

                dataset = MaveDataset.for_scores(StringIO(data))
                dataset.validate()

                self.assertTrue(dataset.is_valid)
                self.assertListEqual(
                    list(dataset.data(serializable=True)[self.SCORE_COL]),
                    [None],
                )

    def test_invalid_null_values_in_header(self):
        for value in null_values_list:
            with self.subTest(msg=f"'{value}'"):
                data = "{},{},{}\n{},1.0,1.0".format(
                    self.HGVS_NT_COL, self.SCORE_COL, value, generate_hgvs()
                )

                dataset = MaveDataset.for_scores(StringIO(data))
                dataset.validate()

                self.assertFalse(dataset.is_valid)
                self.assertEqual(len(dataset.errors), 1)
                print(dataset.errors)

    def test_invalid_no_additional_columns_outside_hgvs_ones(self):
        data = "{},{},{}\n{},{},{}".format(
            self.HGVS_NT_COL,
            self.HGVS_SPLICE_COL,
            self.HGVS_PRO_COL,
            generate_hgvs(prefix="g"),
            generate_hgvs(prefix="c"),
            generate_hgvs(prefix="p"),
        )

        dataset = MaveDataset.for_counts(StringIO(data))
        dataset.validate()

        self.assertFalse(dataset.is_valid)
        self.assertEqual(len(dataset.errors), 1)
        print(dataset.errors)

    def test_scores_missing_scores_column(self):
        data = "{},{}\n{},{}".format(
            self.HGVS_NT_COL,
            "scores_rna",
            generate_hgvs(prefix="g"),
            1.0,
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertFalse(dataset.is_valid)
        self.assertEqual(len(dataset.errors), 1)
        print(dataset.errors)

    def test_invalid_missing_either_required_hgvs_column(self):
        data = "{},{}\n{},{}".format(
            self.HGVS_SPLICE_COL,
            self.SCORE_COL,
            generate_hgvs(prefix="c"),
            1.0,
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertFalse(dataset.is_valid)
        self.assertEqual(len(dataset.errors), 1)
        print(dataset.errors)

    def test_empty_no_variants_parsed(self):
        data = "{},{}\n".format(self.HGVS_NT_COL, self.SCORE_COL)

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertTrue(dataset.is_empty)
        self.assertFalse(dataset.is_valid)
        self.assertEqual(len(dataset.errors), 1)
        print(dataset.errors)

    def test_error_non_numeric_values_in_score_column(self):
        data = "{},{}\n{},{}".format(
            self.HGVS_NT_COL,
            self.SCORE_COL,
            generate_hgvs(prefix="c"),
            "I am not a number",
        )

        with self.assertRaises(ValueError):
            MaveDataset.for_scores(StringIO(data))

    def test_invalid_same_hgvs_nt_defined_in_two_rows(self):
        hgvs = generate_hgvs(prefix="c")
        data = "{},{}\n{},1.0\n{},1.0".format(
            self.HGVS_NT_COL, self.SCORE_COL, hgvs, hgvs
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertFalse(dataset.is_valid)
        self.assertEqual(len(dataset.errors), 1)
        print(dataset.errors)

    def test_invalid_same_variant_defined_in_two_rows_in_hgvs_pro(self):
        hgvs = generate_hgvs(prefix="p")
        data = "{},{}\n{},1.0\n{},1.0".format(
            self.HGVS_PRO_COL, "count", hgvs, hgvs
        )

        dataset = MaveDataset.for_counts(StringIO(data))
        dataset.validate()

        self.assertFalse(dataset.is_valid)
        self.assertEqual(len(dataset.errors), 1)
        print(dataset.errors)

    def test_data_method_converts_null_values_to_None(self):
        hgvs = generate_hgvs()
        for value in null_values_list:
            with self.subTest(msg=value):
                data = "{},{}\n{},{}".format(
                    self.HGVS_NT_COL, self.SCORE_COL, hgvs, value
                )

                dataset = MaveDataset.for_scores(StringIO(data))
                dataset.validate()

                self.assertTrue(dataset.is_valid)

                df = dataset.data(serializable=True)
                self.assertIsNotNone(df[self.HGVS_NT_COL].values[0])
                self.assertIsNone(df[self.SCORE_COL].values[0])

    def test_sorts_header(self):
        hgvs_nt = generate_hgvs(prefix="g")
        hgvs_pro = generate_hgvs(prefix="p")
        hgvs_splice = generate_hgvs(prefix="c")
        data = "{},{},{},{},{}\n{},{},{},{},{}".format(
            self.HGVS_PRO_COL,
            self.HGVS_NT_COL,
            "colA",
            self.SCORE_COL,
            self.HGVS_SPLICE_COL,
            hgvs_pro,
            hgvs_nt,
            "hello",
            1.0,
            hgvs_splice,
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertTrue(dataset.is_valid)
        self.assertListEqual(
            dataset.columns,
            [
                self.HGVS_NT_COL,
                self.HGVS_SPLICE_COL,
                self.HGVS_PRO_COL,
                self.SCORE_COL,
                "colA",
            ],
        )

    def test_does_not_allow_wt_and_sy(self):
        wt = "_wt"
        sy = "_sy"
        data = "{},{},{},{}\n{},{},{},1.0".format(
            self.HGVS_NT_COL,
            self.HGVS_SPLICE_COL,
            self.HGVS_PRO_COL,
            self.SCORE_COL,
            wt,
            wt,
            sy,
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertFalse(dataset.is_valid)
        self.assertEqual(len(dataset.errors), 3)
        print(dataset.errors)

    def test_parses_numeric_column_values_into_float(self):
        hgvs = generate_hgvs(prefix="c")
        data = "{},{}\n{},1.0".format(self.HGVS_NT_COL, self.SCORE_COL, hgvs)

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertTrue(dataset.is_valid)
        value = dataset.data()[self.SCORE_COL].values[0]
        self.assertIsInstance(value, float)

    def test_does_not_split_double_quoted_variants(self):
        hgvs = "c.[123A>G;124A>G]"
        data = '{},{}\n"{}",1.0'.format(self.HGVS_NT_COL, self.SCORE_COL, hgvs)

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertTrue(dataset.is_valid)
        self.assertIn(hgvs, dataset.data()[self.HGVS_NT_COL])

    # def test_invalid_non_double_quoted_multi_variant_row(self):
    #     hgvs = "{},{}".format(generate_hgvs(), generate_hgvs())
    #     data = "{},{}\n'{}',1.0".format(
    #         constants.hgvs_nt_column, required_score_column, hgvs
    #     )
    #     with self.assertRaises(ValidationError):
    #         _ = validate_variant_rows(BytesIO(data.encode()))

    def test_primary_column_is_pro_when_nt_is_not_defined(self):
        hgvs_pro = generate_hgvs(prefix="p")
        data = "{},{}\n{},1.0".format(
            self.HGVS_PRO_COL, self.SCORE_COL, hgvs_pro
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertTrue(dataset.is_valid)
        self.assertEqual(dataset.index_column, self.HGVS_PRO_COL)

    def test_primary_column_is_nt_by_default(self):
        hgvs_nt = generate_hgvs(prefix="c")
        hgvs_pro = generate_hgvs(prefix="p")
        data = "{},{},{}\n{},{},1.0".format(
            self.HGVS_NT_COL,
            self.HGVS_PRO_COL,
            self.SCORE_COL,
            hgvs_nt,
            hgvs_pro,
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertTrue(dataset.is_valid)
        self.assertEqual(dataset.index_column, self.HGVS_NT_COL)

    def test_error_missing_value_in_nt_column_when_nt_is_primary(self):
        for v in null_values_list:
            with self.subTest(msg=v):
                data = (
                    "{},{},{}\n"
                    "{},{},1.0\n"
                    "{},{},1.0".format(
                        self.HGVS_NT_COL,
                        self.HGVS_PRO_COL,
                        self.SCORE_COL,
                        generate_hgvs(prefix="c"),
                        generate_hgvs(prefix="p"),
                        v,
                        generate_hgvs(prefix="p"),
                    )
                )

                dataset = MaveDataset.for_scores(StringIO(data))
                dataset.validate()

                self.assertFalse(dataset.is_valid)
                self.assertEqual(len(dataset.errors), 1)
                print(dataset.errors)

    def test_error_missing_value_in_pro_column_when_pro_is_primary(self):
        for v in null_values_list:
            with self.subTest(msg=v):
                data = "{},{}\n{},1.0\n{},1.0".format(
                    self.HGVS_PRO_COL,
                    self.SCORE_COL,
                    generate_hgvs(prefix="p"),
                    v,
                )

                dataset = MaveDataset.for_scores(StringIO(data))
                dataset.validate()

                self.assertFalse(dataset.is_valid)
                self.assertEqual(len(dataset.errors), 1)
                print(dataset.errors)

    def test_df_indexed_by_primary_column(self):
        data = "{},{},{}\n{},{},1.0".format(
            self.HGVS_NT_COL,
            self.HGVS_PRO_COL,
            self.SCORE_COL,
            generate_hgvs(prefix="c"),
            generate_hgvs(prefix="p"),
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertTrue(dataset.is_valid)
        assert_index_equal(dataset.data().index, dataset.index)

    def test_invalid_duplicates_in_index(self):
        hgvs = generate_hgvs(prefix="c")
        data = "{},{},{}\n{},{},1.0\n{},{},2.0".format(
            self.HGVS_NT_COL,
            self.HGVS_PRO_COL,
            self.SCORE_COL,
            hgvs,
            generate_hgvs(prefix="p"),
            hgvs,
            generate_hgvs(prefix="p"),
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertFalse(dataset.is_valid)
        self.assertEqual(len(dataset.errors), 1)
        print(dataset.errors)

    def test_invalid_hgvs_in_column(self):
        tests = [
            (self.HGVS_PRO_COL, generate_hgvs(prefix="c")),
            (self.HGVS_SPLICE_COL, generate_hgvs(prefix="g")),
            (self.HGVS_NT_COL, generate_hgvs(prefix="p")),
        ]
        for (column, variant) in tests:
            with self.subTest(msg=f"{column}: {variant}"):
                if column == self.HGVS_SPLICE_COL:
                    data = "{},{},{}\n{},{},1.0".format(
                        self.HGVS_NT_COL,
                        column,
                        self.SCORE_COL,
                        generate_hgvs(prefix="g"),
                        variant,
                    )
                else:
                    data = "{},{}\n{},1.0".format(
                        column, self.SCORE_COL, variant
                    )

                dataset = MaveDataset.for_scores(StringIO(data))
                dataset.validate()

                self.assertFalse(dataset.is_valid)
                self.assertEqual(len(dataset.errors), 1)
                print(dataset.errors)

    def test_invalid_genomic_and_transcript_mixed_in_nt_column(self):
        data = "{},{}\n{},1.0\n{},2.0".format(
            self.HGVS_NT_COL,
            self.SCORE_COL,
            generate_hgvs(prefix="g"),
            generate_hgvs(prefix="c"),
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertFalse(dataset.is_valid)
        self.assertEqual(len(dataset.errors), 2)
        print(dataset.errors)

    def test_invalid_nt_not_genomic_when_splice_present(self):
        data = "{},{},{}\n{},{},1.0".format(
            self.HGVS_NT_COL,
            self.HGVS_SPLICE_COL,
            self.SCORE_COL,
            generate_hgvs(prefix="c"),
            generate_hgvs(prefix="c"),
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertFalse(dataset.is_valid)
        self.assertEqual(len(dataset.errors), 1)
        print(dataset.errors)

    def test_invalid_splice_defined_when_nt_is_not(self):
        data = "{},{},{}\n,{},1.0".format(
            self.HGVS_NT_COL,
            self.HGVS_SPLICE_COL,
            self.SCORE_COL,
            generate_hgvs(prefix="c"),
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertFalse(dataset.is_valid)
        self.assertEqual(len(dataset.errors), 1)
        print(dataset.errors)

    def test_invalid_splice_not_defined_when_nt_is_genomic(self):
        data = "{},{}\n{},1.0".format(
            self.HGVS_NT_COL,
            self.SCORE_COL,
            generate_hgvs(prefix="g"),
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertFalse(dataset.is_valid)
        self.assertEqual(len(dataset.errors), 2)
        print(dataset.errors)

    def test_invalid_zero_is_not_parsed_as_none(self):
        hgvs = generate_hgvs(prefix="c")
        data = "{},{}\n{},0.0".format(
            self.HGVS_NT_COL,
            self.SCORE_COL,
            hgvs,
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertTrue(dataset.is_valid)
        df = dataset.data()
        self.assertEqual(df[self.SCORE_COL].values[0], 0)

    def test_invalid_close_to_zero_is_not_parsed_as_none(self):
        hgvs = generate_hgvs(prefix="c")
        data = "{},{}\n{},5.6e-15".format(
            self.HGVS_NT_COL,
            self.SCORE_COL,
            hgvs,
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertTrue(dataset.is_valid)
        df = dataset.data()
        self.assertEqual(df[self.SCORE_COL].values[0], 5.6e-15)

    def test_defines_same_variants(self):
        tests = [
            (
                "{},{}\nc.1A>G,0.0".format(self.HGVS_NT_COL, self.SCORE_COL),
                "{},count\nc.1A>G,0.0".format(self.HGVS_NT_COL),
                True,
            ),
            (
                "{},{}\nc.1A>G,0.0".format(self.HGVS_NT_COL, self.SCORE_COL),
                "{},count\nc.2A>G,0.0".format(self.HGVS_NT_COL),
                False,
            ),
            (
                "{},{},{}\nc.1A>G,p.Ile1Val,0.0".format(
                    self.HGVS_NT_COL,
                    self.HGVS_PRO_COL,
                    self.SCORE_COL,
                ),
                "{},{},count\nc.1A>G,p.Ile1Val,0.0".format(
                    self.HGVS_NT_COL,
                    self.HGVS_PRO_COL,
                ),
                True,
            ),
            (
                "{},{},{}\nc.1A>G,p.Ile1Val,0.0".format(
                    self.HGVS_NT_COL,
                    self.HGVS_PRO_COL,
                    self.SCORE_COL,
                ),
                "{},{},count\nc.1A>G,p.Ile1Phe,0.0".format(
                    self.HGVS_NT_COL,
                    self.HGVS_PRO_COL,
                ),
                False,
            ),
            # Check returns None if either dataset invalid
            (
                "wrong_columns,{}\nc.1A>G,0.0".format(self.SCORE_COL),
                "{},count\nc.1A>G,0.0".format(self.HGVS_NT_COL),
                None,
            ),
            (
                "{},{}\nc.1A>G,0.0".format(self.HGVS_NT_COL, self.SCORE_COL),
                "wrong_column,count\nc.1A>G,0.0".format(),
                None,
            ),
        ]

        for (scores, counts, expected) in tests:
            with self.subTest(msg=(scores, counts, expected)):
                scores_dataset = MaveDataset.for_scores(StringIO(scores))
                scores_dataset.validate()

                counts_dataset = MaveDataset.for_counts(StringIO(counts))
                counts_dataset.validate()

                self.assertEqual(
                    scores_dataset.match_other(counts_dataset),
                    expected,
                )

    def test_to_dict(self):
        hgvs_1 = generate_hgvs(prefix="c")
        hgvs_2 = generate_hgvs(prefix="c")
        data = "{},{},{},{}\n{},,,\n{},,,1.0".format(
            self.HGVS_NT_COL,
            self.HGVS_PRO_COL,
            self.HGVS_SPLICE_COL,
            self.SCORE_COL,
            hgvs_1,
            hgvs_2,
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate()

        self.assertTrue(dataset.is_valid)
        self.assertDictEqual(
            dataset.to_dict(),
            {
                hgvs_1: {
                    self.HGVS_NT_COL: hgvs_1,
                    self.HGVS_SPLICE_COL: None,
                    self.HGVS_PRO_COL: None,
                    self.SCORE_COL: None,
                },
                hgvs_2: {
                    self.HGVS_NT_COL: hgvs_2,
                    self.HGVS_SPLICE_COL: None,
                    self.HGVS_PRO_COL: None,
                    self.SCORE_COL: 1.0,
                },
            },
        )

    def test_valid_targetseq_validation_fails(self):
        data = "{},{},{}\nc.1A>G,p.Ile1Val,0.5".format(
            self.HGVS_NT_COL,
            self.HGVS_PRO_COL,
            self.SCORE_COL,
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate(targetseq="ATC")

        self.assertTrue(dataset.is_valid)

    def test_invalid_targetseq_validation_fails(self):
        data = "{},{},{}\nc.1A>G,p.Val1Phe,0.5".format(
            self.HGVS_NT_COL,
            self.HGVS_PRO_COL,
            self.SCORE_COL,
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate(targetseq="ATC")

        self.assertFalse(dataset.is_valid)
        print(dataset.errors)

        self.assertEqual(dataset.n_errors, 1)
        self.assertIn("p.Val1Phe", dataset.errors[0])

    def test_invalid_target_sequence_not_a_multiple_of_3(self):
        data = "{},{},{}\nc.1A>G,p.Ile1Val,0.5".format(
            self.HGVS_NT_COL,
            self.HGVS_PRO_COL,
            self.SCORE_COL,
        )

        dataset = MaveDataset.for_scores(StringIO(data))
        dataset.validate(targetseq="ATCG")

        self.assertFalse(dataset.is_valid)
        print(dataset.errors)

        self.assertEqual(dataset.n_errors, 1)
        self.assertIn("multiple of 3", dataset.errors[0])

    def test_invalid_relaxed_ordering_check_fails(self):
        self.fail("Test is pending")
