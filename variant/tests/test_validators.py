from io import BytesIO, StringIO

import pandas as pd
from pandas.testing import assert_index_equal, assert_frame_equal

from django.test import TestCase
from django.core.exceptions import ValidationError

from core.utilities import null_values_list

from dataset import constants
from dataset.constants import required_score_column

from .. import constants as hgvs_constants
from ..factories import generate_hgvs, VariantFactory
from ..validators import (
    validate_scoreset_columns_match_variant,
    validate_variant_json,
    validate_variant_rows,
    validate_columns_are_numeric,
    validate_hgvs_nt_uniqueness,
    validate_hgvs_pro_uniqueness,
)
from ..validators.hgvs import validate_hgvs_string


class TestValidateColumnsAreNumeric(TestCase):
    def test_passes_on_special_columns(self):
        df = pd.DataFrame(
            {constants.hgvs_nt_column: ["a"], constants.hgvs_pro_column: ["b"]}
        )
        validate_columns_are_numeric(df)  # Passes

    def test_error_columns_not_float_or_int(self):
        df = pd.DataFrame({required_score_column: ["a"]})
        with self.assertRaises(ValidationError):
            validate_columns_are_numeric(df)


class TestValidateMatchingColumns(TestCase):
    """
    Tests the function :func:`validate_scoreset_columns_match_variant` which
    throws a `ValidationError` if the keys of a variant's data do not match
    the corresponding columns defined in the parent
    :class:`dataset.models.scoreset.ScoreSet`.
    """

    def test_validationerror_non_matching_score_columns(self):
        variant = VariantFactory()
        with self.assertRaises(ValidationError):
            variant.data[constants.variant_score_data] = {}
            validate_scoreset_columns_match_variant(
                variant.scoreset.dataset_columns, variant.data
            )

    def test_validationerror_non_matching_count_columns(self):
        variant = VariantFactory()
        with self.assertRaises(ValidationError):
            variant.data[constants.variant_count_data] = {"count": 1}
            validate_scoreset_columns_match_variant(
                variant.scoreset.dataset_columns, variant.data
            )

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
        validate_scoreset_columns_match_variant(
            variant.scoreset.dataset_columns, variant.data
        )


class TestHGVSValidator(TestCase):
    """
    Tests the function :func:`validate_hgvs_string` to see if it is able
    to validate strings which do not comply with the HGVS standard for
    coding, non-coding and nucleotide variants and multi-variants.
    """

    def test_validation_error_not_str_or_bytes(self):
        with self.assertRaises(ValidationError):
            validate_hgvs_string([])

    def test_passes_wt_hgvs(self):
        validate_hgvs_string("_wt")

    def test_passes_sy_hgvs(self):
        validate_hgvs_string("_sy")

    def test_passes_multi(self):
        validate_hgvs_string("p.[Lys4Gly;C34_G35insTGC]")
        validate_hgvs_string("c.[1A>G;127_128delinsAGC]")

    def test_error_invalid_hgvs(self):
        with self.assertRaises(ValidationError):
            validate_hgvs_string("c.ad")

    def test_converts_bytes_to_string_before_validation(self):
        validate_hgvs_string(b"r.427a>g")

    def test_return_none_for_null(self):
        for c in null_values_list:
            self.assertIsNone(validate_hgvs_string(c))


class TestVariantJsonValidator(TestCase):
    """
    Tests the validator :func:`validate_variant_json` to check if the correct
    errors are thrown if an incorrectly formatted `dictionary` is set
    as a the `data` `JSONField` attribute of a :class:`..models.Variant`
    instance.
    """

    def test_validationerror_missing_score_data_key(self):
        data = {constants.variant_count_data: {}}
        with self.assertRaises(ValidationError):
            validate_variant_json(data)

    def test_validationerror_missing_count_data_key(self):
        data = {constants.variant_score_data: {}}
        with self.assertRaises(ValidationError):
            validate_variant_json(data)

    def test_validationerror_constains_unexpected_keys(self):
        data = {
            "extra": {},
            constants.variant_score_data: {},
            constants.variant_count_data: {},
        }
        with self.assertRaises(ValidationError):
            validate_variant_json(data)

    def test_validationerror_values_not_dict(self):
        data = {
            constants.variant_score_data: {},
            constants.variant_count_data: {},
        }
        for key in data.keys():
            data[key] = []
            with self.assertRaises(ValidationError):
                validate_variant_json(data)
            data[key] = {}


class TestVariantRowValidator(TestCase):
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

    @staticmethod
    def mock_return_value(data, index=None):
        df = pd.read_csv(StringIO(data), sep=",", na_values=["None", None])
        if index:
            df.index = pd.Index(df[index])
        return df

    def test_validationerror_row_hgvs_is_not_a_string(self):
        data = "{},{}\n1.0,1.0".format(
            constants.hgvs_nt_column, required_score_column
        )
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))

    def test_validationerror_missing_hgvs_columns(self):
        data = "{},{}\n{},1.0".format(
            "not_hgvs", required_score_column, generate_hgvs()
        )
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))

    def test_strip_whitespace_from_columns(self):
        hgvs = generate_hgvs()
        data = " {} , {} \n {} , 1.0 ".format(
            constants.hgvs_nt_column, required_score_column, hgvs
        )
        non_hgvs_cols, _, df = validate_variant_rows(BytesIO(data.encode()))
        self.assertListEqual(non_hgvs_cols, [required_score_column])
        expected = pd.DataFrame(
            {
                constants.hgvs_nt_column: [hgvs],
                constants.hgvs_pro_column: [None],
                constants.required_score_column: [1.0],
            }
        )
        expected.index = expected[constants.hgvs_nt_column]
        assert_frame_equal(df, expected)

    def test_replaces_null_with_none_in_secondary_hgvs_column(self):
        hgvs_nt = generate_hgvs(prefix="c")
        for c in null_values_list:
            data = "{},{},{}\n{},{},1.0 ".format(
                constants.hgvs_nt_column,
                constants.hgvs_pro_column,
                required_score_column,
                hgvs_nt,
                c,
            )
            non_hgvs_cols, _, df = validate_variant_rows(
                BytesIO(data.encode())
            )
            self.assertIsNone(df[constants.hgvs_pro_column].values[0])

    def test_replaces_null_with_none_in_numeric_columns(self):
        hgvs_nt = generate_hgvs(prefix="c")
        for c in null_values_list:
            data = "{},{}\n{},{}".format(
                constants.hgvs_nt_column, required_score_column, hgvs_nt, c
            )
            non_hgvs_cols, _, df = validate_variant_rows(
                BytesIO(data.encode())
            )
            self.assertIsNone(df[constants.required_score_column].values[0])

    def test_validationerror_null_values_in_hgvs_column(self):
        for value in null_values_list:
            data = "{},{}\n{},1.0".format(
                constants.hgvs_nt_column, value, generate_hgvs()
            )
            with self.assertRaises(ValidationError):
                validate_variant_rows(BytesIO(data.encode()))

    def test_validationerror_no_numeric_columns(self):
        data = "{},{}\n{},{}".format(
            constants.hgvs_nt_column,
            constants.hgvs_pro_column,
            generate_hgvs(prefix="c"),
            generate_hgvs(prefix="p"),
        )
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))

    def test_validationerror_no_variants_parsed(self):
        data = "{},{}\n".format(
            constants.hgvs_nt_column, required_score_column
        )
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))

    def test_validationerror_non_numeric_values_non_hgvs_columns(self):
        data = "{},{}\n{},hello world".format(
            constants.hgvs_nt_column, required_score_column, generate_hgvs()
        )
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))

    def test_validationerror_same_hgvs_nt_defined_in_two_rows(self):
        hgvs = generate_hgvs(prefix="c")
        data = "{},{}\n{},1.0\n{},1.0".format(
            constants.hgvs_nt_column, required_score_column, hgvs, hgvs
        )
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))

    def test_allows_same_hgvs_pro_defined_in_two_rows(self):
        hgvs = generate_hgvs(prefix="p")
        data = "{},{}\n{},1.0\n{},1.0".format(
            constants.hgvs_pro_column, required_score_column, hgvs, hgvs
        )
        validate_variant_rows(BytesIO(data.encode()))  # passes

    def test_null_values_converted_to_None(self):
        hgvs = generate_hgvs()
        for value in null_values_list:
            data = "{},{}\n{},{}".format(
                constants.hgvs_nt_column, required_score_column, hgvs, value
            )
            non_hgvs_cols, _, df = validate_variant_rows(
                BytesIO(data.encode())
            )
            self.assertIsNotNone(df[constants.hgvs_nt_column].values[0])
            self.assertIsNone(df[constants.required_score_column].values[0])

    def test_returns_sorted_header_with_score_col_first(self):
        hgvs_nt = generate_hgvs(prefix="c")
        hgvs_pro = generate_hgvs(prefix="p")
        data = "{},{},a,{}\n{},{},1.0,1.0".format(
            constants.hgvs_nt_column,
            constants.hgvs_pro_column,
            required_score_column,
            hgvs_nt,
            hgvs_pro,
        )
        header, _, _ = validate_variant_rows(BytesIO(data.encode()))
        expected = [required_score_column, "a"]
        self.assertEqual(header, expected)

    def test_allows_wt_and_sy(self):
        wt = hgvs_constants.wildtype
        sy = hgvs_constants.synonymous
        data = "{},{},{}\n{},{},1.0".format(
            constants.hgvs_nt_column,
            constants.hgvs_pro_column,
            required_score_column,
            wt,
            sy,
        )
        non_hgvs_cols, _, df = validate_variant_rows(BytesIO(data.encode()))
        self.assertEqual(df[constants.hgvs_nt_column].values[0], wt)
        self.assertEqual(df[constants.hgvs_pro_column].values[0], sy)

    # TODO: Un-comment if changing format_variant call
    # def test_converts_qmark_to_xaa_in_protein_sub(self):
    #     data = "{},{}\n{},1.0".format(
    #         constants.hgvs_pro_column, required_score_column, "p.Gly4???"
    #     )
    #     non_hgvs_cols, _, df = validate_variant_rows(BytesIO(data.encode()))
    #     self.assertEqual(df[constants.hgvs_nt_column].values[0], None)
    #     self.assertEqual(df[constants.hgvs_pro_column].values[0], "p.Gly4Xaa")
    #
    # def test_converts_triple_x_to_single_n_rna_dna(self):
    #     data = "{},{}\n{},1.0\n{},2.0".format(
    #         constants.hgvs_nt_column, required_score_column, "c.1A>X", "r.1a>x"
    #     )
    #     non_hgvs_cols, _, df = validate_variant_rows(BytesIO(data.encode()))
    #     self.assertEqual(df[constants.hgvs_nt_column].values[0], "c.1A>N")
    #     self.assertEqual(df[constants.hgvs_nt_column].values[1], "r.1a>n")
    #
    # def test_converts_qmarks_to_xaa_in_protein_multi_sub(self):
    #     data = "{},{}\n{},1.0".format(
    #         constants.hgvs_pro_column,
    #         required_score_column,
    #         "p.[Gly4???;Asp2???]",
    #     )
    #     non_hgvs_cols, _, df = validate_variant_rows(BytesIO(data.encode()))
    #     self.assertEqual(df[constants.hgvs_nt_column].values[0], None)
    #     self.assertEqual(
    #         df[constants.hgvs_pro_column].values[0], "p.[Gly4Xaa;Asp2Xaa]"
    #     )
    #
    # def test_converts_triple_x_to_single_n_in_multi_rna_dna(self):
    #     data = "{},{}\n{},1.0\n{},2.0".format(
    #         constants.hgvs_nt_column,
    #         required_score_column,
    #         "n.[1A>X;1_2delinsXXX]",
    #         "r.[1a>x;1_2insxxx]",
    #     )
    #     non_hgvs_cols, _, df = validate_variant_rows(BytesIO(data.encode()))
    #     self.assertEqual(
    #         df[constants.hgvs_nt_column].values[0], "n.[1A>N;1_2delinsNNN]"
    #     )
    #     self.assertEqual(
    #         df[constants.hgvs_nt_column].values[1], "r.[1a>n;1_2insnnn]"
    #     )

    def test_parses_numeric_column_values_into_float(self):
        hgvs = generate_hgvs()
        data = "{},{}\n{},1.0".format(
            constants.hgvs_nt_column, required_score_column, hgvs
        )
        _, _, df = validate_variant_rows(BytesIO(data.encode()))
        value = df[required_score_column].values[0]
        self.assertIsInstance(value, float)

    def test_does_not_split_double_quoted_variants(self):
        hgvs = "r.[123a>g,19del,9002_9009delins(5)]"
        data = '{},{}\n"{}",1.0'.format(
            constants.hgvs_nt_column, required_score_column, hgvs
        )
        _, primary, df = validate_variant_rows(BytesIO(data.encode()))
        self.assertIn(hgvs, df[constants.hgvs_nt_column])

    def test_validationerror_non_double_quoted_multi_variant_row(self):
        hgvs = "{},{}".format(generate_hgvs(), generate_hgvs())
        data = "{},{}\n'{}',1.0".format(
            constants.hgvs_nt_column, required_score_column, hgvs
        )
        with self.assertRaises(ValidationError):
            _ = validate_variant_rows(BytesIO(data.encode()))

    def test_primary_column_is_pro_when_nt_is_not_defined(self):
        hgvs_pro = generate_hgvs(prefix="p")
        data = "{},{}\n{},1.0".format(
            constants.hgvs_pro_column, required_score_column, hgvs_pro
        )
        _, primary, _ = validate_variant_rows(BytesIO(data.encode()))
        self.assertEqual(primary, constants.hgvs_pro_column)

    def test_primary_column_is_nt_by_default(self):
        hgvs_nt = generate_hgvs(prefix="c")
        hgvs_pro = generate_hgvs(prefix="p")
        data = "{},{},{}\n{},{},1.0".format(
            constants.hgvs_nt_column,
            constants.hgvs_pro_column,
            required_score_column,
            hgvs_nt,
            hgvs_pro,
        )
        _, primary, _ = validate_variant_rows(BytesIO(data.encode()))
        self.assertEqual(primary, constants.hgvs_nt_column)

    def test_error_missing_value_in_nt_column_when_nt_is_primary(self):
        hgvs_nt = generate_hgvs(prefix="c")
        for v in null_values_list:
            data = "{},{},{}\n{},{},1.0".format(
                constants.hgvs_nt_column,
                constants.hgvs_pro_column,
                required_score_column,
                v,
                hgvs_nt,
            )
            with self.assertRaises(ValidationError):
                validate_variant_rows(BytesIO(data.encode()))

    def test_error_missing_value_in_pro_column_when_pro_is_primary(self):
        for v in null_values_list:
            data = "{},{}\n{},1.0".format(
                constants.hgvs_pro_column, required_score_column, v
            )
            with self.assertRaises(ValidationError):
                validate_variant_rows(BytesIO(data.encode()))

    def test_df_indexed_by_primary_column(self):
        hgvs_nt = generate_hgvs(prefix="c")
        hgvs_pro = generate_hgvs(prefix="p")

        data = "{},{},{}\n{},{},1.0".format(
            constants.hgvs_nt_column,
            constants.hgvs_pro_column,
            required_score_column,
            hgvs_nt,
            hgvs_pro,
        )
        _, primary, df = validate_variant_rows(BytesIO(data.encode()))
        assert_index_equal(df.index, pd.Index(df[primary]))

    def test_validationerror_nt_variant_in_pro_column(self):
        hgvs = generate_hgvs(prefix="c")
        data = "{},{}\n{},1.0".format(
            constants.hgvs_pro_column, required_score_column, hgvs
        )
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))

    def test_validationerror_pro_variant_in_nt_column(self):
        hgvs = generate_hgvs(prefix="p")
        data = "{},{}\n{},1.0".format(
            constants.hgvs_nt_column, required_score_column, hgvs
        )
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))

    def test_validationerror_zero_is_not_parsed_as_none(self):
        hgvs = generate_hgvs(prefix="c")
        data = "{},{}\n{},0.0".format(
            constants.hgvs_nt_column, required_score_column, hgvs
        )
        _, _, df = validate_variant_rows(BytesIO(data.encode()))
        self.assertEqual(df[required_score_column].values[0], 0)

    def test_validationerror_close_to_zero_is_not_parsed_as_none(self):
        hgvs = generate_hgvs(prefix="c")
        data = "{},{}\n{},5.6e-15".format(
            constants.hgvs_nt_column, required_score_column, hgvs
        )
        _, _, df = validate_variant_rows(BytesIO(data.encode()))
        self.assertEqual(df[required_score_column].values[0], 5.6e-15)


class TestValidateNtUniqueness(TestCase):
    def test_error_redefined(self):
        df = pd.DataFrame({constants.hgvs_nt_column: ["c.1A>G", "c.1A>G"]})
        with self.assertRaises(ValidationError):
            validate_hgvs_nt_uniqueness(df)

    def test_passes_on_unique(self):
        df = pd.DataFrame({constants.hgvs_nt_column: ["c.1A>G", "c.2A>G"]})
        validate_hgvs_nt_uniqueness(df)


class TestValidateProUniqueness(TestCase):
    def test_error_redefined(self):
        df = pd.DataFrame({constants.hgvs_pro_column: ["p.G4L", "p.G4L"]})
        with self.assertRaises(ValidationError):
            validate_hgvs_pro_uniqueness(df)

    def test_passes_on_unique(self):
        df = pd.DataFrame({constants.hgvs_pro_column: ["p.G4L", "p.G5L"]})
        validate_hgvs_pro_uniqueness(df)
