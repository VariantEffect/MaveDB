from io import BytesIO, StringIO

from django.test import TestCase
from django.core.exceptions import ValidationError

from ..constants import (
    nan_col_values, hgvs_column,
    score_columns, count_columns, meta_columns
)
from ..validators import (
    validate_scoreset_count_data_input,
    validate_scoreset_score_data_input,
    validate_scoreset_meta_data_input,
    validate_at_least_two_columns,
    validate_has_hgvs_in_header,
    validate_header_contains_no_null_columns,
    read_header_from_io,
    validate_scoreset_json
)


class TestHeaderFromIO(TestCase):
    """
    Tests to ensure that a file in bytes or string mode can be read and then
    returned to the start so there are no side effects for later reading the
    files.
    """
    def test_can_read_header_from_bytes(self):
        file = BytesIO("{},score,count\n".format(hgvs_column).encode())
        header = read_header_from_io(file)
        expected = [hgvs_column, 'score', 'count']
        self.assertEqual(expected, header)

    def test_removes_quotes_from_header(self):
        file = BytesIO(
            "\"{}\",\"score\",\'count\'\n".format(hgvs_column).encode())
        header = read_header_from_io(file)
        expected = [hgvs_column, 'score', 'count']
        self.assertEqual(expected, header)

    def test_can_read_header_from_string(self):
        file = StringIO("{},score,count\n".format(hgvs_column))
        header = read_header_from_io(file)
        expected = [hgvs_column, 'score', 'count']
        self.assertEqual(expected, header)

    def test_returns_file_position_to_begining(self):
        file = BytesIO("{},score,count\n".format(hgvs_column).encode())
        read_header_from_io(file)
        self.assertEqual(
            file.read(),
            "{},score,count\n".format(hgvs_column).encode()
        )


class TestNoNullInColumnsValidator(TestCase):
    """
    Tests to ensure that an input file contains no null values in the header
    such as '', None, null etc.
    """
    def test_raises_validationerror_when_null_values_in_column(self):
        for value in nan_col_values:
            file = BytesIO("{},score,{}\n".format(hgvs_column, value).encode())
            with self.assertRaises(ValidationError):
                header = read_header_from_io(file)
                validate_header_contains_no_null_columns(header)

    def test_does_not_raise_validationerror_when_non_null_values_in_column(self):
        file = BytesIO("{},score\n".format(hgvs_column).encode())
        header = read_header_from_io(file)
        validate_header_contains_no_null_columns(header)  # Should pass


class TestAtLeastTwoColumnsValidator(TestCase):
    """
    Tests to ensure that an input file contains at least two columns.
    """
    def test_raises_validationerror_when_less_than_2_values_in_column(self):
        file = BytesIO("{}\n".format(hgvs_column).encode())
        with self.assertRaises(ValidationError):
            header = read_header_from_io(file)
            validate_at_least_two_columns(header)

    def test_does_not_raise_validationerror_2_or_more_values_in_column(self):
        file = BytesIO("{},score,count\n".format(hgvs_column).encode())
        header = read_header_from_io(file)
        validate_at_least_two_columns(header)  # Should pass

        file = BytesIO("{},score\n".format(hgvs_column).encode())
        header = read_header_from_io(file)
        validate_at_least_two_columns(header)  # Should pass


class TestHgvsInHeaderValidator(TestCase):
    """
    Tests that case-sensitive 'hgvs' is in the header of a file.
    """
    def test_raises_validationerror_when_hgvs_not_in_column(self):
        file = BytesIO("score,count\n".encode())
        with self.assertRaises(ValidationError):
            header = read_header_from_io(file)
            validate_has_hgvs_in_header(header)

    def test_hgvs_must_be_lowercase(self):
        file = BytesIO("HGVS,score,count\n".encode())
        with self.assertRaises(ValidationError):
            header = read_header_from_io(file)
            validate_has_hgvs_in_header(header)

    def test_does_not_raise_validationerror_when_hgvs_in_column(self):
        file = BytesIO("{},score,count\n".format(hgvs_column).encode())
        header = read_header_from_io(file)
        validate_at_least_two_columns(header)  # Should pass


class TestValidateScoreSetCountDataInputValidator(TestCase):
    """
    Tests that validation errors are thrown when an ill-formatted count data
    input file is supplied.
    """
    def test_raises_validationerror_when_hgvs_not_in_column(self):
        file = BytesIO("score,count\n".encode())
        with self.assertRaises(ValidationError):
            validate_scoreset_count_data_input(file)

    def test_raises_validationerror_when_less_than_2_values_in_column(self):
        file = BytesIO("{}\n".format(hgvs_column).encode())
        with self.assertRaises(ValidationError):
            validate_scoreset_count_data_input(file)

    def test_raises_validationerror_when_null_values_in_column(self):
        for value in nan_col_values:
            file = BytesIO("{},score,{}\n".format(hgvs_column, value).encode())
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

    def test_raises_validationerror_when_less_than_2_values_in_column(self):
        file = BytesIO("{}\n".format(hgvs_column).encode())
        with self.assertRaises(ValidationError):
            validate_scoreset_score_data_input(file)

    def test_raises_validationerror_when_null_values_in_column(self):
        for value in nan_col_values:
            file = BytesIO("{},score,{}\n".format(hgvs_column, value).encode())
            with self.assertRaises(ValidationError):
                validate_scoreset_score_data_input(file)

    def test_validatation_error_score_not_in_header(self):
        file = BytesIO("{},count\n".format(hgvs_column).encode())
        with self.assertRaises(ValidationError):
            validate_scoreset_score_data_input(file)


class TestValidateScoreSetMetaDataInputValidator(TestCase):
    """
    Tests that validation errors are thrown when an ill-formatted metadata
    input file is supplied.
    """
    def test_raises_validationerror_when_hgvs_not_in_column(self):
        file = BytesIO("score,count\n".encode())
        with self.assertRaises(ValidationError):
            validate_scoreset_meta_data_input(file)

    def test_raises_validationerror_when_less_than_2_values_in_column(self):
        file = BytesIO("{}\n".format(hgvs_column).encode())
        with self.assertRaises(ValidationError):
            validate_scoreset_meta_data_input(file)

    def test_raises_validationerror_when_null_values_in_column(self):
        for value in nan_col_values:
            file = BytesIO("{},score,{}\n".format(hgvs_column, value).encode())
            with self.assertRaises(ValidationError):
                validate_scoreset_meta_data_input(file)


class TestValidateScoreSetJsonValidator(TestCase):
    """
    Test to ensure that a scoreset json field is properly formatted.
    """
    def test_validationerror_unexptected_columns(self):
        field = {
            'extra_column': [],
            score_columns: ['score'],
            count_columns: [],
            meta_columns: []
        }
        with self.assertRaises(ValidationError):
            validate_scoreset_json(field)

    def test_validationerror_values_not_lists(self):
        field = {
            score_columns: ['score'],
            count_columns: {},
            meta_columns: {}
        }
        with self.assertRaises(ValidationError):
            validate_scoreset_json(field)

    def test_validationerror_list_values_not_strings(self):
        field = {
            score_columns: [b'score'],
            count_columns: [],
            meta_columns: []
        }
        with self.assertRaises(ValidationError):
            validate_scoreset_json(field)

    def test_validationerror_empty_score_columns(self):
        field = {
            score_columns: [],
            count_columns: [],
            meta_columns: []
        }
        with self.assertRaises(ValidationError):
            validate_scoreset_json(field)

    def test_validationerror_missing_dict_columns(self):
        # score_columns missing
        field = {
            count_columns: [],
            meta_columns: []
        }
        with self.assertRaises(ValidationError):
            validate_scoreset_json(field)

        # count_columns missing
        field = {
            score_columns: ['score'],
            meta_columns: []
        }
        with self.assertRaises(ValidationError):
            validate_scoreset_json(field)

        # metadata_columns missing
        field = {
            score_columns: ['score'],
            count_columns: []
        }
        with self.assertRaises(ValidationError):
            validate_scoreset_json(field)

    def test_validationerror_missing_header_columns(self):
        # score_columns columns missing 'score'
        field = {
            score_columns: ['hgvs'],
            count_columns: [],
            meta_columns: []
        }
        with self.assertRaises(ValidationError):
            validate_scoreset_json(field)