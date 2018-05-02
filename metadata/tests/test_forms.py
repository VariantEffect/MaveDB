from django.test import TestCase

from dataset.constants import nan_col_values
from genome.factories import TargetGeneFactory

from ..factories import (
    UniprotIdentifierFactory,
    EnsemblIdentifierFactory,
    RefseqIdentifierFactory,
    UniprotOffsetFactory,
)
from ..models import (
    UniprotIdentifier, EnsemblIdentifier, RefseqIdentifier,
    UniprotOffset, RefseqOffset, EnsemblOffset
)
from ..forms import UniprotOffsetForm, EnsemblOffsetForm, RefseqOffsetForm


class TestBaseOffsetForm(TestCase):
    """
    Tests the base `<IE>OffsetForm` using :class:`UniprotOffsetForm` as the
    driver.
    """
    @staticmethod
    def form_data():
        return {
            "identifier": "",
            "offset": 0,
        }

    @staticmethod
    def types():
        return [
            (
                UniprotIdentifierFactory, UniprotOffsetForm,
                UniprotOffset, UniprotIdentifier, 'P19174'
            ),
            (
                EnsemblIdentifierFactory, EnsemblOffsetForm,
                EnsemblOffset, EnsemblIdentifier, 'ENSG00000006062'
            ),
            (
                RefseqIdentifierFactory, RefseqOffsetForm,
                RefseqOffset, RefseqIdentifier, 'WP_107309473.1'
            ),
        ]

    def test_can_create_new_identifiers(self):
        for (factory, form_class, offset_class, id_class, new) in self.types():
            data = self.form_data()
            data['identifier'] = new
            target = TargetGeneFactory(
                uniprot_id=None, refseq_id=None, ensembl_id=None)

            form = form_class(data=data)
            self.assertTrue(form.is_valid())

            offset = form.save(target=target, commit=True)
            self.assertEqual(offset.identifier.identifier, data['identifier'])
            self.assertEqual(offset_class.objects.count(), 1)
            self.assertEqual(id_class.objects.count(), 1)

    def test_retrieves_existing_identifiers(self):
        for (factory, form_class, offset_class, id_class, _) in self.types():
            up = factory()
            data = self.form_data()
            data['identifier'] = up.identifier
            target = TargetGeneFactory(
                uniprot_id=None, refseq_id=None, ensembl_id=None)

            form = form_class(data=data)
            self.assertTrue(form.is_valid())

            offset = form.save(target=target, commit=True)
            self.assertEqual(offset.identifier.identifier, data['identifier'])
            self.assertEqual(offset_class.objects.count(), 1)
            self.assertEqual(id_class.objects.count(), 1)

    def test_valid_if_all_fields_blank(self):
        data = {}
        form = UniprotOffsetForm(data=data)
        self.assertTrue(form.is_valid())

    def test_save_associates_target(self):
        data = self.form_data()
        data['identifier'] = "P12345"
        target = TargetGeneFactory()

        form = UniprotOffsetForm(data=data)
        self.assertTrue(form.is_valid())

        offset = form.save(target=target, commit=True)
        self.assertEqual(offset.target, target)

    def test_value_error_save_without_target(self):
        data = self.form_data()
        data['identifier'] = "P12345"
        form = UniprotOffsetForm(data=data)
        self.assertTrue(form.is_valid())
        with self.assertRaises(ValueError):
            form.save(commit=True)

    def test_valid_empty_identifier(self):
        for value in nan_col_values:
            data = self.form_data()
            data['identifier'] = value
            form = UniprotOffsetForm(data=data)
            self.assertTrue(form.is_valid())

    def test_invalid_negative_offset(self):
        data = self.form_data()
        data['identifier'] = "P12345"
        data['offset'] = -1
        form = UniprotOffsetForm(data=data)
        self.assertFalse(form.is_valid())

    def test_instance_populates_initial_identifier(self):
        instance = UniprotOffsetFactory()
        form = UniprotOffsetForm(instance=instance, data={})
        self.assertEqual(
            form.fields['identifier'].initial, instance.identifier)
        self.assertTrue(form.is_valid())

    def test_instance_populates_initial_offset(self):
        instance = UniprotOffsetFactory()
        form = UniprotOffsetForm(instance=instance, data={})
        self.assertEqual(
            form.fields['offset'].initial, instance.offset)
        self.assertTrue(form.is_valid())

    def test_deletes_self_when_blank(self):
        data = self.form_data()
        instance = UniprotOffsetFactory()
        data['identifier'] = ""
        form = UniprotOffsetForm(data=data, instance=instance)
        self.assertTrue(form.is_valid())
        instance = form.save(commit=True)
        self.assertEqual(UniprotOffset.objects.count(), 0)
        self.assertIsNone(instance)
