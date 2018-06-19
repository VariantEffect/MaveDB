from io import BytesIO

from django.test import TestCase
from django.core.exceptions import ValidationError

from dataset import constants
from dataset.constants import required_score_column

from ..hgvs import constants as hgvs_constants
from ..factories import generate_hgvs, VariantFactory
from ..validators import (
    validate_hgvs_string,
    validate_scoreset_columns_match_variant,
    validate_variant_json,
    validate_variant_rows
)


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
                variant.scoreset.dataset_columns, variant.data)

    def test_validationerror_non_matching_count_columns(self):
        variant = VariantFactory()
        with self.assertRaises(ValidationError):
            variant.data[constants.variant_count_data] = {'count': 1}
            validate_scoreset_columns_match_variant(
                variant.scoreset.dataset_columns, variant.data)

    def test_compares_sorted_columns(self):
        variant = VariantFactory()
        variant.data[constants.variant_score_data] = {
            'other': 1, constants.required_score_column: 1}
        variant.scoreset.dataset_columns[constants.score_columns] = [
            constants.required_score_column, 'other']
        # This should pass
        validate_scoreset_columns_match_variant(
                variant.scoreset.dataset_columns, variant.data)


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
        validate_hgvs_string('_wt')
    
    def test_passes_sy_hgvs(self):
        validate_hgvs_string('_sy')
        
    def test_passes_multi(self):
        validate_hgvs_string('p.[Lys4Gly;C34_G35insTGC]')
        validate_hgvs_string('c.[1A>G;127_128delinsAGC]')
        
    def test_error_invalid_hgvs(self):
        with self.assertRaises(ValidationError):
            validate_hgvs_string('c.ad')
            
    def test_converts_bytes_to_string_before_validation(self):
        validate_hgvs_string(b'r.427a>g')
    
    def test_error_null(self):
        for c in constants.nan_col_values:
            with self.assertRaises(ValidationError):
                validate_hgvs_string(c)
        

class TestVariantJsonValidator(TestCase):
    """
    Tests the validator :func:`validate_variant_json` to check if the correct
    errors are thrown if an incorrectly formatted `dictionary` is set
    as a the `data` `JSONField` attribute of a :class:`..models.Variant`
    instance.
    """
    def test_validationerror_missing_score_data_key(self):
        data = {
            constants.variant_count_data: {},
        }
        with self.assertRaises(ValidationError):
            validate_variant_json(data)

    def test_validationerror_missing_count_data_key(self):
        data = {
            constants.variant_score_data: {},
        }
        with self.assertRaises(ValidationError):
            validate_variant_json(data)

    def test_validationerror_constains_unexpected_keys(self):
        data = {
            'extra': {},
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
    def test_validationerror_row_hgvs_is_not_a_string(self):
        data = "{},{}\n1.0,1.0".format(
            constants.hgvs_nt_column, required_score_column)
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))

    def test_validationerror_missing_hgvs_columns(self):
        data = "{},{}\n{},1.0".format(
            'not_hgvs', required_score_column, generate_hgvs())
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))

    def test_strip_whitespace_from_header_columns(self):
        data = " {} , {} \n{},1.0".format(
            constants.hgvs_nt_column, required_score_column, generate_hgvs())
        header, _, _ = validate_variant_rows(BytesIO(data.encode()))
        self.assertEqual(header, [required_score_column])

    def test_validationerror_null_values_in_hgvs_column(self):
        for value in constants.nan_col_values:
            data = "{},{}\n{},1.0".format(
                constants.hgvs_nt_column, value, generate_hgvs())
            with self.assertRaises(ValidationError):
                validate_variant_rows(BytesIO(data.encode()))
    
    def test_secondary_hgvs_allows_null_values(self):
        for value in constants.nan_col_values:
            data = "{},{},{}\n{},{},1.0".format(
                constants.hgvs_nt_column,
                constants.hgvs_pro_column,
                constants.required_score_column,
                generate_hgvs(prefix='c'), value)
            _, _, hgvs_map = validate_variant_rows(BytesIO(data.encode()))
            self.assertIsNone(
                list(hgvs_map.values())[0][constants.hgvs_pro_column]
            )

    def test_validationerror_no_numeric_columns(self):
        data = "{},{}\n{}".format(
            constants.hgvs_nt_column, constants.hgvs_pro_column,
            generate_hgvs(prefix='c'), generate_hgvs(prefix='p')
        )
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))

    def test_validationerror_no_variants_parsed(self):
        data = "{},{}\n".format(constants.hgvs_nt_column, required_score_column)
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))

    def test_validationerror_invalid_hgvs(self):
        with self.assertRaises(ValidationError):
            validate_hgvs_string('c.1A>G (p.Lys4Gly)')
            
    def test_valid_wt_sy(self):
        validate_hgvs_string('_wt')
        validate_hgvs_string('_sy')

    def test_validationerror_non_numeric_values_non_hgvs_columns(self):
        data = "{},{}\n{},hello world".format(
            constants.hgvs_nt_column, required_score_column, generate_hgvs())
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))

    def test_validationerror_same_hgvs_defined_in_two_rows(self):
        hgvs = generate_hgvs()
        data = "{},{}\n{},1.0\n{},1.0".format(
            constants.hgvs_nt_column, required_score_column, hgvs, hgvs)
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))

    def test_null_values_converted_to_None(self):
        hgvs = generate_hgvs()
        for value in constants.nan_col_values:
            data = "{},{}\n{},{}".format(
                constants.hgvs_nt_column, required_score_column, hgvs, value)
            header, _, hgvs_map = validate_variant_rows(BytesIO(data.encode()))
            expected_map = {
                hgvs: {
                    required_score_column: None,
                    constants.hgvs_nt_column: hgvs,
                    constants.hgvs_pro_column: None
                }
            }
            expected_header = [required_score_column]
            self.assertEqual(header, expected_header)
            self.assertEqual(dict(hgvs_map), expected_map)

    def test_returns_sorted_header(self):
        hgvs_nt = generate_hgvs(prefix='c')
        hgvs_pro = generate_hgvs(prefix='p')
        data = "{},{},a,{}\n{},{},1.0,1.0".format(
            constants.hgvs_nt_column,
            constants.hgvs_pro_column,
            required_score_column, hgvs_nt, hgvs_pro)
        header, _, _ = validate_variant_rows(BytesIO(data.encode()))
        expected = [required_score_column, 'a']
        self.assertEqual(header, expected)
        
    def test_allows_wt_and_sy(self):
        wt = hgvs_constants.wildtype
        sy = hgvs_constants.synonymous
        data = "{},{},{}\n{},{},1.0".format(
            constants.hgvs_nt_column,
            constants.hgvs_pro_column,
            required_score_column, wt, sy)
        header, _, hgvs_map = validate_variant_rows(BytesIO(data.encode()))
        self.assertEqual(hgvs_map[wt][constants.hgvs_nt_column], wt)
        self.assertEqual(hgvs_map[wt][constants.hgvs_pro_column], sy)

    def test_hgvs_columns_filtered_from_row_data(self):
        hgvs_nt = generate_hgvs(prefix='c')
        hgvs_pro = generate_hgvs(prefix='p')
        data = "{},{},{}\n{},{},1.0".format(
            constants.hgvs_nt_column,
            constants.hgvs_pro_column,
            required_score_column,
            hgvs_nt, hgvs_pro
        )
        header, primary, hgvs_map = validate_variant_rows(BytesIO(data.encode()))
        self.assertEqual(list(hgvs_map[primary].keys()), [required_score_column])
        self.assertEqual(header, [required_score_column])

    def test_parses_numeric_column_values_into_float(self):
        hgvs = generate_hgvs()
        data = "{},{}\n{},1.0".format(
            constants.hgvs_nt_column, required_score_column, hgvs)
        _, _, hgvs_map = validate_variant_rows(BytesIO(data.encode()))
        value = hgvs_map[hgvs][required_score_column]
        self.assertIsInstance(value, float)

    def test_does_not_split_double_quoted_variants(self):
        hgvs = 'r.[123a>g,19del,9002_9009delins(5)]'
        data = '{},{}\n"{}",1.0'.format(
            constants.hgvs_nt_column, required_score_column, hgvs)
        _, primary, hgvs_map = validate_variant_rows(BytesIO(data.encode()))
        self.assertIn(hgvs, hgvs_map)

    def test_validationerror_non_double_quoted_multi_variant_row(self):
        hgvs = '{},{}'.format(generate_hgvs(), generate_hgvs())
        data = "{},{}\n'{}',1.0".format(
            constants.hgvs_nt_column, required_score_column, hgvs)
        with self.assertRaises(ValidationError):
            _ = validate_variant_rows(BytesIO(data.encode()))
    
    def test_primary_column_is_nt_when_pro_is_also_defined(self):
        hgvs_nt = generate_hgvs(prefix='c')
        hgvs_pro = generate_hgvs(prefix='p')
        data = "{},{},{}\n{},{},1.0".format(
            constants.hgvs_nt_column,
            constants.hgvs_pro_column,
            required_score_column,
            hgvs_nt, hgvs_pro
        )
        header, primary, hgvs_map = validate_variant_rows(
            BytesIO(data.encode()))
        self.assertEqual(primary, constants.hgvs_nt_column)

    def test_primary_column_is_pro_when_nt_is_not_defined(self):
        hgvs_pro = generate_hgvs(prefix='p')
        data = "{},{}\n{},1.0".format(
            constants.hgvs_pro_column,
            required_score_column,
            hgvs_pro
        )
        header, primary, hgvs_map = validate_variant_rows(
            BytesIO(data.encode()))
        self.assertEqual(primary, constants.hgvs_pro_column)
        
    def test_primary_column_is_nt_by_default(self):
        hgvs_nt = generate_hgvs(prefix='c')
        data = "{},{}\n{},1.0".format(
            constants.hgvs_nt_column,
            required_score_column,
            hgvs_nt
        )
        header, primary, hgvs_map = validate_variant_rows(
            BytesIO(data.encode()))
        self.assertEqual(primary, constants.hgvs_nt_column)

    def test_error_missing_value_in_nt_column_when_nt_is_primary(self):
        hgvs_nt = generate_hgvs(prefix='c')
        hgvs_pro = generate_hgvs(prefix='p')
        
        data = "{},{},{}\n,{},1.0".format(
            constants.hgvs_nt_column,
            constants.hgvs_pro_column,
            required_score_column,
            hgvs_nt, hgvs_pro
        )
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))

    def test_error_missing_value_in_pro_column_when_pro_is_primary(self):
        hgvs_pro = generate_hgvs(prefix='p')
        data = "{},{}\n,1.0".format(
            constants.hgvs_pro_column,
            required_score_column, hgvs_pro
        )
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))
        
    def test_hgvs_map_indexed_by_nt_column_when_nt_is_primary(self):
        hgvs_nt = generate_hgvs(prefix='c')
        hgvs_pro = generate_hgvs(prefix='p')
    
        data = "{},{},{}\n{},{},1.0".format(
            constants.hgvs_nt_column,
            constants.hgvs_pro_column,
            required_score_column,
            hgvs_nt, hgvs_pro
        )
        _, primary, hgvs_map = validate_variant_rows(BytesIO(data.encode()))
        self.assertEqual(primary, constants.hgvs_nt_column)
        self.assertIsNotNone(hgvs_map.get(hgvs_nt))

    def test_hgvs_map_indexed_by_pro_column_when_pro_is_primary(self):
        hgvs_pro = generate_hgvs(prefix='p')
        data = "{},{}\n{},1.0".format(
            constants.hgvs_pro_column,
            required_score_column,
            hgvs_pro
        )
        _, primary, hgvs_map = validate_variant_rows(BytesIO(data.encode()))
        self.assertEqual(primary, constants.hgvs_pro_column)
        self.assertIsNotNone(hgvs_map.get(hgvs_pro))
    
    def test_validationerror_nt_variant_in_pro_column(self):
        hgvs = generate_hgvs(prefix='c')
        data = "{},{}\n{},1.0".format(
            constants.hgvs_pro_column,
            required_score_column, hgvs
        )
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))
        
    def test_validationerror_pro_variant_in_nt_column(self):
        hgvs = generate_hgvs(prefix='p')
        data = "{},{}\n{},1.0".format(
            constants.hgvs_nt_column,
            required_score_column, hgvs
        )
        with self.assertRaises(ValidationError):
            validate_variant_rows(BytesIO(data.encode()))