from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.test import TestCase

import dataset.constants as constants
from dataset.factories import ScoreSetFactory

from ..factories import VariantFactory


class TestVariant(TestCase):
    """
    The purpose of this unit test is to test that the database model
    :py:class:`ScoreSet`, representing an experiment with associated
    :py:class:`Variant` objects. We will test correctness of creation,
    validation, uniqueness, queries and that the appropriate errors are raised.
    """

    def test_autoassign_urn_when_save(self):
        variant = VariantFactory()
        scoreset = variant.scoreset
        urn = "{}#{}".format(scoreset.urn, scoreset.last_child_value)
        self.assertEqual(variant.urn, urn)

    def test_create_urn_increments_last_child_value_by_one(self):
        scoreset = ScoreSetFactory()
        before_variant = scoreset.last_child_value
        _ = VariantFactory(scoreset=scoreset)
        after_variant = scoreset.last_child_value
        self.assertEqual(before_variant + 1, after_variant)

    def test_cannot_create_variant_with_duplicate_urn(self):
        variant = VariantFactory()
        with self.assertRaises(IntegrityError):
            _ = VariantFactory(urn=variant.urn)

    def test_cannot_save_without_scoreset(self):
        with self.assertRaises(IntegrityError):
            _ = VariantFactory(scoreset=None)

    def test_cannot_save_without_hgvs(self):
        with self.assertRaises(IntegrityError):
            _ = VariantFactory(hgvs=None)

    def test_validation_error_json_has_no_scores_key(self):
        var = VariantFactory(data={
            constants.variant_count_data: {},
            constants.variant_metadata: {}
        })
        with self.assertRaises(ValidationError):
            var.full_clean()

    def test_validation_error_json_has_no_counts_key(self):
        var = VariantFactory(data={
            constants.variant_score_data: {constants.required_score_column: 1},
            constants.variant_metadata: {}
        })
        with self.assertRaises(ValidationError):
            var.full_clean()

    def test_validation_error_json_has_no_meta_key(self):
        var = VariantFactory(data={
            constants.variant_count_data: {},
            constants.variant_score_data: {constants.required_score_column: 1}
        })
        with self.assertRaises(ValidationError):
            var.full_clean()

    def test_validation_error_data_missing_required_score_column(self):
        var = VariantFactory(data={
            constants.variant_metadata: {},
            constants.variant_count_data: {},
            constants.variant_score_data: {}
        })
        with self.assertRaises(ValidationError):
            var.full_clean()
