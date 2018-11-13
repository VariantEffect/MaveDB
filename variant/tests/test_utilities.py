import pandas as pd
import numpy as np

from django.test import TestCase
from django.core.exceptions import ValidationError

from dataset import constants

from .. import utilities


class TestCreateVariantAttrsUtility(TestCase):
    @staticmethod
    def fixture_data(nt_score=('c.1A>G', 'c.2A>G'),
                     pro_score=('p.G1L', 'p.G1L'),
                     nt_count=('c.1A>G', 'c.2A>G'),
                     pro_count=('p.G1L', 'p.G1L'),
                     index=constants.hgvs_nt_column):
        score_df = pd.DataFrame({
            constants.hgvs_nt_column: nt_score,
            constants.hgvs_pro_column: pro_score,
            constants.required_score_column: [3.1, 3.2]
         }, index=nt_score if index == constants.hgvs_nt_column else pro_score)
        count_df = pd.DataFrame({
            constants.hgvs_nt_column: nt_count,
            constants.hgvs_pro_column: pro_count,
            'count': [1, 2]
        }, index=nt_count if index == constants.hgvs_nt_column else pro_count)
        return score_df, count_df
    
    def test_returns_empty_list_if_score_df_is_empty(self):
        d1, d2 = self.fixture_data()
        self.assertListEqual([], utilities.convert_df_to_variant_records(
            pd.DataFrame(), d2
        ))
        self.assertListEqual([], utilities.convert_df_to_variant_records(
            None, d2
        ))
        self.assertListEqual([], utilities.convert_df_to_variant_records(
            '[]', d2
        ))
        
    def test_can_load_from_json_records(self):
        d1, d2 = self.fixture_data(index=constants.hgvs_pro_column)
        variants = utilities.convert_df_to_variant_records(
            d1.to_json(orient='records'), d2.to_json(orient='records'),
            index=constants.hgvs_pro_column
        )
        expected = [
            {
                constants.hgvs_nt_column: 'c.1A>G',
                constants.hgvs_pro_column: 'p.G1L',
                'data': {
                    constants.variant_score_data: {
                        constants.required_score_column: 3.1},
                    constants.variant_count_data: {'count': 1}
                }
            },
            {
                constants.hgvs_nt_column: 'c.2A>G',
                constants.hgvs_pro_column: 'p.G1L',
                'data': {
                    constants.variant_score_data: {
                        constants.required_score_column: 3.2},
                    constants.variant_count_data: {'count': 2}
                }
            }
        ]
        self.assertListEqual(variants, expected)
        
    def test_will_group_matching_records_when_index_contains_duplicates(self):
        d1, d2 = self.fixture_data(index=constants.hgvs_pro_column)
        variants = utilities.convert_df_to_variant_records(d1, d2)
        expected = [
            {
                constants.hgvs_nt_column: 'c.1A>G',
                constants.hgvs_pro_column: 'p.G1L',
                'data': {
                    constants.variant_score_data: {
                        constants.required_score_column: 3.1},
                    constants.variant_count_data: {'count': 1}
                }
            },
            {
                constants.hgvs_nt_column: 'c.2A>G',
                constants.hgvs_pro_column: 'p.G1L',
                'data': {
                    constants.variant_score_data: {
                        constants.required_score_column: 3.2},
                    constants.variant_count_data: {'count': 2}
                }
            }
        ]
        self.assertListEqual(variants, expected)
        
    def test_will_group_matching_records_when_index_contains_uniques(self):
        d1, d2 = self.fixture_data(
            index=constants.hgvs_nt_column,
            pro_count=('p.G1L', 'p.G2L'),
            pro_score=('p.G1L', 'p.G2L'),
        )
        variants = utilities.convert_df_to_variant_records(d1, d2)
        expected = [
            {
                constants.hgvs_nt_column: 'c.1A>G',
                constants.hgvs_pro_column: 'p.G1L',
                'data': {
                    constants.variant_score_data: {
                        constants.required_score_column: 3.1},
                    constants.variant_count_data: {'count': 1}
                }
            },
            {
                constants.hgvs_nt_column: 'c.2A>G',
                constants.hgvs_pro_column: 'p.G2L',
                'data': {
                    constants.variant_score_data: {
                        constants.required_score_column: 3.2},
                    constants.variant_count_data: {'count': 2}
                }
            }
        ]
        self.assertListEqual(variants, expected)
        
    def test_group_ordering_is_maintained(self):
        d1, d2 = self.fixture_data(
            index=constants.hgvs_nt_column,
            nt_score=('c.2A>G', 'c.1A>G'),
            nt_count=('c.1A>G', 'c.2A>G'),
        )
        variants = utilities.convert_df_to_variant_records(d1, d2)
        expected = [
            {
                constants.hgvs_nt_column: 'c.2A>G',
                constants.hgvs_pro_column: 'p.G1L',
                'data': {
                    constants.variant_score_data: {
                        constants.required_score_column: 3.1},
                    constants.variant_count_data: {'count': 2}
                }
            },
            {
                constants.hgvs_nt_column: 'c.1A>G',
                constants.hgvs_pro_column: 'p.G1L',
                'data': {
                    constants.variant_score_data: {
                        constants.required_score_column: 3.2},
                    constants.variant_count_data: {'count': 1}
                }
            }
        ]
        self.assertListEqual(variants, expected)
        
    def test_empty_variant_count_data_when_no_counts_detected(self):
        d1, _ = self.fixture_data()
        variants = utilities.convert_df_to_variant_records(d1, None)
        expected = [
            {
                constants.hgvs_nt_column: 'c.1A>G',
                constants.hgvs_pro_column: 'p.G1L',
                'data': {
                    constants.variant_score_data: {
                        constants.required_score_column: 3.1},
                    constants.variant_count_data: {}
                }
            },
            {
                constants.hgvs_nt_column: 'c.2A>G',
                constants.hgvs_pro_column: 'p.G1L',
                'data': {
                    constants.variant_score_data: {
                        constants.required_score_column: 3.2},
                    constants.variant_count_data: {}
                }
            }
        ]
        self.assertListEqual(variants, expected)
        
    def test_error_index_mismatch(self):
        d1, d2 = self.fixture_data(
            index=constants.hgvs_nt_column, nt_score=('c.4A>G', 'c.2A>G'))
        with self.assertRaises(AssertionError):
            utilities.convert_df_to_variant_records(d1, d2)
            
    def test_index_are_sorted_before_comparison(self):
        d1, d2 = self.fixture_data(
            index=constants.hgvs_nt_column, nt_score=('c.2A>G', 'c.1A>G'))
        utilities.convert_df_to_variant_records(d1, d2)  # passes
        
    def test_error_nt_variant_mismatch(self):
        d1, d2 = self.fixture_data(
            index=constants.hgvs_pro_column, nt_score=('c.4A>G', 'c.2A>G'))
        with self.assertRaises(ValidationError):
            utilities.convert_df_to_variant_records(d1, d2)
        
    def test_error_pro_variant_mismatch(self):
        d1, d2 = self.fixture_data(
            index=constants.hgvs_nt_column, pro_score=('p.G1L', 'p.G2L'))
        with self.assertRaises(ValidationError):
            utilities.convert_df_to_variant_records(d1, d2)
        
    def test_returns_record_for_each_row_in_index(self):
        d1, d2 = self.fixture_data()
        result = utilities.convert_df_to_variant_records(d1, d2)
        self.assertEqual(len(result), len(d1))
        self.assertEqual(len(result), len(d2))

    def test_sets_index_when_column_name_is_passed(self):
        d1, d2 = self.fixture_data(
            index=constants.hgvs_pro_column,
            pro_count=('p.G1L', 'p.G2L')
        ) # Raises error since pro index should not match
        with self.assertRaises(AssertionError):
            utilities.convert_df_to_variant_records(
                d1, d2, index=constants.hgvs_pro_column
            )

    def test_converts_np_nan_to_none(self):
        d1, d2 = self.fixture_data()
        d1[constants.required_score_column] = np.NaN
        d2['count'] = np.NaN

        variants = utilities.convert_df_to_variant_records(d1, d2)
        self.assertIsNone(
            variants[0]['data'][constants.variant_score_data][
                constants.required_score_column])
        self.assertIsNone(
            variants[0]['data'][constants.variant_count_data]['count'])

        self.assertIsNone(
            variants[1]['data'][constants.variant_score_data][
                constants.required_score_column])
        self.assertIsNone(
            variants[1]['data'][constants.variant_count_data]['count'])
