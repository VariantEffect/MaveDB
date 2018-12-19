from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.test import TestCase, mock

from dataset.models.scoreset import ScoreSet
import dataset.constants as constants
from dataset.factories import ScoreSetFactory
from dataset.utilities import publish_dataset

from ..factories import VariantFactory
from ..models import assign_public_urn, Variant

from urn.validators import MAVEDB_VARIANT_URN_RE


class TestVariant(TestCase):
    """
    The purpose of this unit test is to test that the database model
    :py:class:`ScoreSet`, representing an experiment with associated
    :py:class:`Variant` objects. We will test correctness of creation,
    validation, uniqueness, queries and that the appropriate errors are raised.
    """

    def test_autoassign_urn_when_save(self):
        variant = VariantFactory()
        self.assertIsNotNone(variant.urn)

    def test_cannot_create_variant_with_duplicate_urn(self):
        variant = VariantFactory()
        with self.assertRaises(IntegrityError):
            _ = VariantFactory(urn=variant.urn)

    def test_cannot_save_without_scoreset(self):
        with self.assertRaises(IntegrityError):
            _ = VariantFactory(scoreset=None)

    def test_validation_error_json_has_no_scores_key(self):
        var = VariantFactory(data={
            constants.variant_count_data: {},
        })
        with self.assertRaises(ValidationError):
            var.full_clean()

    def test_validation_error_json_has_no_counts_key(self):
        var = VariantFactory(data={
            constants.variant_score_data: {constants.required_score_column: 1},
        })
        with self.assertRaises(ValidationError):
            var.full_clean()

    def test_validation_error_data_missing_required_score_column(self):
        var = VariantFactory(data={
            constants.variant_count_data: {},
            constants.variant_score_data: {}
        })
        with self.assertRaises(ValidationError):
            var.full_clean()
            
    def test_variant_created_with_tmp_urn(self):
        scs = ScoreSetFactory()
        obj = VariantFactory(scoreset=scs)
        self.assertIn('tmp', obj.urn)
        
    def test_hgvs_property_returns_nt_if_both_protein_defined(self):
        obj = VariantFactory()
        self.assertEqual(obj.hgvs, obj.hgvs_nt)
        
    def test_hgvs_property_returns_pro_if_nt_column_not_defined(self):
        obj = VariantFactory(hgvs_nt=None)
        self.assertEqual(obj.hgvs, obj.hgvs_pro)
        
    def test_bulk_create_urns_creates_sequential_urns(self):
        parent = ScoreSetFactory()
        urns = Variant.bulk_create_urns(10, parent)
        for i, urn in enumerate(urns):
            number = int(urn.split('#')[-1])
            self.assertEqual(number, i + 1)
            
    def test_bulk_create_urns_updates_parent_last_child_value(self):
        parent = ScoreSetFactory()
        Variant.bulk_create_urns(10, parent)
        self.assertEqual(parent.last_child_value, 10)
    
    @mock.patch.object(Variant, 'bulk_create_urns', return_value=['',])
    def test_bulk_create_calls_bulk_create_urns_with_correct_args(self, patch):
        parent = ScoreSetFactory()
        column = constants.required_score_column
        variant_kwargs_list = [{
            'hgvs_nt': 'c.1A>G', 'hgvs_pro': 'p.G4Y',
            'data': dict({
                constants.variant_score_data: {column: 1},
                constants.variant_count_data: {},}),
            }, {
            'hgvs_nt': 'c.2A>G', 'hgvs_pro': 'p.G5Y',
            'data': dict({
                constants.variant_score_data: {column: 2},
                constants.variant_count_data: {}, }),
            },
        ]
        _ = Variant.bulk_create(parent, variant_kwargs_list)
        patch.assert_called_with(*(2, parent))
        
    def test_bulk_create_creates_variants_with_kwargs(self):
        parent = ScoreSetFactory()
        column = constants.required_score_column
        variant_kwargs_list = [{
            'hgvs_nt': 'c.1A>G', 'hgvs_pro': 'p.G4Y',
            'data': dict({
                constants.variant_score_data: {column: 1},
                constants.variant_count_data: {},}),
            }, {
            'hgvs_nt': 'c.2A>G', 'hgvs_pro': 'p.G5Y',
            'data': dict({
                constants.variant_score_data: {column: 2},
                constants.variant_count_data: {}, }),
            },
        ]
        count = Variant.bulk_create(parent, variant_kwargs_list)
        self.assertEqual(count, 2)

        parent.refresh_from_db()
        variants = parent.variants.order_by('urn')
        self.assertEqual(variants[0].urn, '{}#{}'.format(parent.urn, 1))
        self.assertEqual(variants[0].hgvs_nt, 'c.1A>G')
        self.assertEqual(variants[0].hgvs_pro, 'p.G4Y')
        self.assertDictEqual(variants[0].data, variant_kwargs_list[0]['data'])
        
        self.assertEqual(variants[1].urn, '{}#{}'.format(parent.urn, 2))
        self.assertEqual(variants[1].hgvs_nt, 'c.2A>G')
        self.assertEqual(variants[1].hgvs_pro, 'p.G5Y')
        self.assertDictEqual(variants[1].data, variant_kwargs_list[1]['data'])
        
        
class TestAssignPublicUrn(TestCase):
    def setUp(self):
        self.private_scoreset = ScoreSetFactory()
        self.public_scoreset = publish_dataset(ScoreSetFactory())
        
    def test_assigns_public_urn(self):
        instance = VariantFactory(scoreset=self.public_scoreset)
        instance = assign_public_urn(instance)
        self.assertIsNotNone(MAVEDB_VARIANT_URN_RE.fullmatch(instance.urn))
        self.assertTrue(instance.has_public_urn)
        
    def test_increments_parent_last_child_value(self):
        instance = VariantFactory(scoreset=self.public_scoreset)
        self.assertEqual(instance.scoreset.last_child_value, 0)
        instance = assign_public_urn(instance)
        self.assertEqual(instance.scoreset.last_child_value, 1)
        
    def test_attr_error_parent_not_public(self):
        instance = VariantFactory(scoreset=self.private_scoreset)
        with self.assertRaises(AttributeError):
            assign_public_urn(instance)
        
    def test_attr_error_parent_has_tmp_urn(self):
        instance = VariantFactory(scoreset=self.private_scoreset)
        self.private_scoreset.private = False
        self.private_scoreset.save()
        with self.assertRaises(AttributeError):
            assign_public_urn(instance)
        
    def test_assigns_sequential_urns(self):
        instance1 = VariantFactory(scoreset=self.public_scoreset)
        instance2 = VariantFactory(scoreset=self.public_scoreset)
        instance1 = assign_public_urn(instance1)
        instance2 = assign_public_urn(instance2)
        self.assertEqual(int(instance1.urn[-1]), 1)
        self.assertEqual(int(instance2.urn[-1]), 2)
        
    def test_applying_twice_does_not_change_urn(self):
        instance = VariantFactory(scoreset=self.public_scoreset)
        self.assertEqual(
            assign_public_urn(instance).urn,
            assign_public_urn(instance).urn
        )
