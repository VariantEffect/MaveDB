from django.core.exceptions import ValidationError
from django.test import TestCase

import dataset.constants as constants

from ..factories import KeywordFactory
from ..fields import ModelSelectMultipleField
from ..models import Keyword


class TestModelSelectMultipleField(TestCase):
    """
    Tests the :class:`ModelSelectMultipleField` which handles being able
    to select existing M2M relationships or create new ones, for example
    if a user wishes to create a new keyword not in the database.
    """
    def tearDown(self):
        Keyword.objects.all().delete()

    def test_check_values_filters_out_null_values(self):
        field = ModelSelectMultipleField(
            klass=Keyword, to_field_name='text',
            queryset=Keyword.objects.none()
        )
        for value in constants.nan_col_values:
            existing = field._check_values([value])
            self.assertEqual(existing.count(), 0)
            self.assertEqual(len(field.new_values), 0)

    def test_new_values_detected(self):
        field = ModelSelectMultipleField(
            klass=Keyword, to_field_name='text',
            queryset=Keyword.objects.none()
        )
        values = ['hello', 'world']
        qs = field.clean(values)
        self.assertEqual(qs.count(), 0)
        self.assertEqual(len(field.new_values), 2)
        self.assertEqual(len(field.new_instances), 0)

    def test_new_value_not_created_if_exists_in_new_instances(self):
        field = ModelSelectMultipleField(
            klass=Keyword, to_field_name='text',
            queryset=Keyword.objects.none()
        )
        field.new_instances = [Keyword(text='protein')]
        qs = field.clean(['protein'])
        self.assertEqual(qs.count(), 0)
        self.assertEqual(len(field.new_instances), 1)
        self.assertEqual(len(field.new_values), 0)

    def test_new_value_not_created_if_exists_in_new_values(self):
        field = ModelSelectMultipleField(
            klass=Keyword, to_field_name='text',
            queryset=Keyword.objects.none()
        )
        field.new_values = ['protein']
        qs = field.clean(['protein'])
        self.assertEqual(qs.count(), 0)
        self.assertEqual(len(field.new_instances), 0)
        self.assertEqual(len(field.new_values), 1)

    def test_existing_db_values_pass_on_to_super_check_values(self):
        kw = KeywordFactory()
        field = ModelSelectMultipleField(
            klass=Keyword, to_field_name='text',
            queryset=Keyword.objects.all()
        )
        qs = field._check_values([kw.text])
        self.assertEqual(qs.count(), 1)
        self.assertEqual(len(field.new_instances), 0)
        self.assertEqual(len(field.new_values), 0)

    def test_create_new_creates_new_instances(self):
        field = ModelSelectMultipleField(
            klass=Keyword, to_field_name='text',
            queryset=Keyword.objects.none()
        )
        values = ['protein']
        field.clean(values)
        new = field.create_new()
        self.assertEqual(new[0].text, values[0])

        field.save_new()
        self.assertEqual(Keyword.objects.count(), 1)
