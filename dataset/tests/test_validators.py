from io import BytesIO, StringIO

import pandas as pd

from django.test import TestCase
from django.core.exceptions import ValidationError

from core.utilities import null_values_list

from .. import constants
from ..validators import (
    validate_scoreset_count_data_input,
    validate_scoreset_score_data_input,
    validate_at_least_one_additional_column,
    validate_has_hgvs_in_header,
    validate_header_contains_no_null_columns,
    read_header_from_io,
    validate_scoreset_json,
    validate_datasets_define_same_variants,
    WordLimitValidator,
)


class TestWordLimitValidator(TestCase):
    def test_validation_error_more_than_word_limit(self):
        with self.assertRaises(ValidationError):
            n = 5
            WordLimitValidator(n)("Word " * (n + 1))

    def test_passes_equal_to_word_limit(self):
        n = 5
        WordLimitValidator(n)("Word " * n)

    def test_passes_less_than_word_limit(self):
        n = 5
        WordLimitValidator(n)("Word " * (n - 1))


class TestHeaderFromIO(TestCase):
    """
    Tests to ensure that a file in bytes or string mode can be read and then
    returned to the start so there are no side effects for later reading the
    files.
    """

    def test_can_read_header_from_bytes(self):
        file = BytesIO(
            "{},score,count\n".format(constants.hgvs_nt_column).encode()
        )
        header = read_header_from_io(file)
        expected = [constants.hgvs_nt_column, "score", "count"]
        self.assertEqual(expected, header)

    def test_removes_quotes_from_header(self):
        file = BytesIO(
            '"{}","score","count,nt"\n'.format(
                constants.hgvs_nt_column
            ).encode()
        )
        header = read_header_from_io(file)
        expected = [constants.hgvs_nt_column, "score", "count,nt"]
        self.assertEqual(expected, header)

    def test_can_read_header_from_string(self):
        file = StringIO("{},score,count\n".format(constants.hgvs_nt_column))
        header = read_header_from_io(file)
        expected = [constants.hgvs_nt_column, "score", "count"]
        self.assertEqual(expected, header)

    def test_strips_whitespace(self):
        file = StringIO(
            " {} ,   score ,  count\n".format(constants.hgvs_nt_column)
        )
        header = read_header_from_io(file)
        expected = [constants.hgvs_nt_column, "score", "count"]
        self.assertEqual(expected, header)

    def test_returns_file_position_to_begining(self):
        file = BytesIO(
            "{},score,count\n".format(constants.hgvs_nt_column).encode()
        )
        read_header_from_io(file)
        self.assertEqual(
            file.read(),
            "{},score,count\n".format(constants.hgvs_nt_column).encode(),
        )


class TestNoNullInColumnsValidator(TestCase):
    """
    Tests to ensure that an input file contains no null values in the header
    such as '', None, null etc.
    """

    def test_raises_validationerror_when_null_values_in_column(self):
        for value in null_values_list:
            file = BytesIO(
                "{},score,{}\n".format(
                    constants.hgvs_nt_column, value
                ).encode()
            )
            with self.assertRaises(ValidationError):
                header = read_header_from_io(file)
                validate_header_contains_no_null_columns(header)

    def test_does_not_raise_validationerror_when_non_null_values_in_column(
        self,
    ):
        file = BytesIO("{},score\n".format(constants.hgvs_nt_column).encode())
        header = read_header_from_io(file)
        validate_header_contains_no_null_columns(header)  # Should pass


class TestAtLeastOneNumericColumnValidator(TestCase):
    """
    Tests to ensure that an input file contains at least two columns.
    """

    def test_raises_validationerror_when_less_than_2_values_in_column(self):
        file = BytesIO("{}\n".format(constants.hgvs_nt_column).encode())
        with self.assertRaises(ValidationError):
            header = read_header_from_io(file)
            validate_at_least_one_additional_column(header)

    def test_does_not_raise_validationerror_2_or_more_values_in_column(self):
        file = BytesIO(
            "{},score,count\n".format(constants.hgvs_nt_column).encode()
        )
        header = read_header_from_io(file)
        validate_at_least_one_additional_column(header)  # Should pass

        file = BytesIO("{},score\n".format(constants.hgvs_nt_column).encode())
        header = read_header_from_io(file)
        validate_at_least_one_additional_column(header)  # Should pass


class TestHgvsInHeaderValidator(TestCase):
    """
    Tests that case-sensitive 'hgvs' is in the header of a file.
    """

    def test_raises_validationerror_when_neither_hgvs_col_in_column(self):
        file = BytesIO("score,count\n".encode())
        with self.assertRaises(ValidationError):
            header = read_header_from_io(file)
            validate_has_hgvs_in_header(header)

    def test_hgvs_must_be_lowercase(self):
        file = BytesIO(
            "{},score,count\n".format(
                constants.hgvs_nt_column.upper()
            ).encode()
        )
        with self.assertRaises(ValidationError):
            header = read_header_from_io(file)
            validate_has_hgvs_in_header(header)

    def test_does_not_raise_validationerror_when_either_hgvs_in_column(self):
        file = BytesIO(
            "{},score,count\n".format(constants.hgvs_nt_column).encode()
        )
        header = read_header_from_io(file)
        validate_has_hgvs_in_header(header)  # Should pass

        file = BytesIO(
            "{},score,count\n".format(constants.hgvs_pro_column).encode()
        )
        header = read_header_from_io(file)
        validate_has_hgvs_in_header(header)  # Should pass


class TestValidateScoreCountsDefineSameVariants(TestCase):
    """
    Tests that an uploaded score/counts files define the same variants
    in both the _nt column and _pro column.
    """

    def test_ve_counts_defines_different_nt_variants(self):
        scores = pd.DataFrame(
            {
                constants.hgvs_nt_column: ["c.1A>G"],
                constants.hgvs_pro_column: [None],
                constants.hgvs_splice_column: [None],
            }
        )
        counts = pd.DataFrame(
            {
                constants.hgvs_nt_column: ["c.2A>G"],
                constants.hgvs_pro_column: [None],
                constants.hgvs_splice_column: [None],
            }
        )
        with self.assertRaises(ValidationError):
            validate_datasets_define_same_variants(scores, counts)

    def test_ve_counts_defines_different_splice_variants(self):
        scores = pd.DataFrame(
            {
                constants.hgvs_nt_column: [None],
                constants.hgvs_splice_column: ["c.1A>G"],
                constants.hgvs_pro_column: [None],
            }
        )
        counts = pd.DataFrame(
            {
                constants.hgvs_nt_column: [None],
                constants.hgvs_splice_column: ["c.2A>G"],
                constants.hgvs_pro_column: [None],
            }
        )
        with self.assertRaises(ValidationError):
            validate_datasets_define_same_variants(scores, counts)

    def test_ve_counts_defines_different_pro_variants(self):
        scores = pd.DataFrame(
            {
                constants.hgvs_nt_column: [None],
                constants.hgvs_splice_column: [None],
                constants.hgvs_pro_column: ["p.Leu5Glu"],
            }
        )
        counts = pd.DataFrame(
            {
                constants.hgvs_nt_column: [None],
                constants.hgvs_splice_column: [None],
                constants.hgvs_pro_column: ["p.Leu75Glu"],
            }
        )
        with self.assertRaises(ValidationError):
            validate_datasets_define_same_variants(scores, counts)

    def test_passes_when_same_variants_defined(self):
        scores = pd.DataFrame(
            {
                constants.hgvs_nt_column: ["c.1A>G"],
                constants.hgvs_pro_column: ["p.Leu5Glu"],
                constants.hgvs_splice_column: ["c.1A>G"],
            }
        )
        counts = pd.DataFrame(
            {
                constants.hgvs_nt_column: ["c.1A>G"],
                constants.hgvs_pro_column: ["p.Leu5Glu"],
                constants.hgvs_splice_column: ["c.1A>G"],
            }
        )
        validate_datasets_define_same_variants(scores, counts)


class TestValidateScoreSetCountDataInputValidator(TestCase):
    """
    Tests that validation errors are thrown when an ill-formatted count data
    input file is supplied.
    """

    def test_raises_validationerror_when_hgvs_not_in_column(self):
        file = BytesIO("score,count\n".encode())
        with self.assertRaises(ValidationError):
            validate_scoreset_count_data_input(file)

    def test_raises_validationerror_no_numeric_column(self):
        file = BytesIO("{}\n".format(constants.hgvs_nt_column).encode())
        with self.assertRaises(ValidationError):
            validate_scoreset_count_data_input(file)

    def test_raises_validationerror_when_null_values_in_column(self):
        for value in null_values_list:
            file = BytesIO(
                "{},score,{}\n".format(
                    constants.hgvs_nt_column, value
                ).encode()
            )
            with self.assertRaises(ValidationError):
                validate_scoreset_count_data_input(file)


class TestValidateScoreSetScoreDataInputValidator(TestCase):
    """
    Tests that validation errors are thrown when an ill-formatted score data
    input file is supplied.
    """

    def test_raises_validationerror_when_hgvs_not_in_column(self):
        file = BytesIO("score,count\n".encode())
        with self.assertRaises(ValidationError):
            validate_scoreset_score_data_input(file)

    def test_raises_validationerror_no_numeric_column(self):
        file = BytesIO("{}\n".format(constants.hgvs_nt_column).encode())
        with self.assertRaises(ValidationError):
            validate_scoreset_score_data_input(file)

    def test_raises_validationerror_when_null_values_in_column(self):
        for value in null_values_list:
            file = BytesIO(
                "{},score,{}\n".format(
                    constants.hgvs_nt_column, value
                ).encode()
            )
            with self.assertRaises(ValidationError):
                validate_scoreset_score_data_input(file)

    def test_validatation_error_score_not_in_header(self):
        file = BytesIO("{},count\n".format(constants.hgvs_nt_column).encode())
        with self.assertRaises(ValidationError):
            validate_scoreset_score_data_input(file)


class TestValidateScoreSetJsonValidator(TestCase):
    """
    Test to ensure that a scoreset json field is properly formatted.
    """

    def test_validationerror_unexptected_columns(self):
        field = {
            "extra_column": [],
            constants.score_columns: ["score"],
            constants.count_columns: [],
        }
        with self.assertRaises(ValidationError):
            validate_scoreset_json(field)

    def test_validationerror_values_not_lists(self):
        field = {
            constants.score_columns: ["score"],
            constants.count_columns: {},
        }
        with self.assertRaises(ValidationError):
            validate_scoreset_json(field)

    def test_validationerror_list_values_not_strings(self):
        field = {
            constants.score_columns: [b"score"],
            constants.count_columns: [],
        }
        with self.assertRaises(ValidationError):
            validate_scoreset_json(field)

    def test_validationerror_empty_score_columns(self):
        field = {constants.score_columns: [], constants.count_columns: []}
        with self.assertRaises(ValidationError):
            validate_scoreset_json(field)

    def test_validationerror_missing_dict_columns(self):
        # constants.score_columns missing
        field = {constants.count_columns: []}
        with self.assertRaises(ValidationError):
            validate_scoreset_json(field)

        # constants.count_columns missing
        field = {constants.score_columns: ["score"]}
        with self.assertRaises(ValidationError):
            validate_scoreset_json(field)

    def test_validationerror_missing_header_columns(self):
        # constants.score_columns columns missing 'score'
        field = {
            constants.score_columns: ["hgvs"],
            constants.count_columns: [],
        }
        with self.assertRaises(ValidationError):
            validate_scoreset_json(field)
