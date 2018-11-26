from django.test import TestCase

from core.utilities import null_values_list

from ..factories import KeywordFactory
from ..fields import FlexibleModelChoiceField, FlexibleModelMultipleChoiceField
from ..models import Keyword


class TestFlexibleModelMultipleChoiceField(TestCase):
    """
    Tests the :class:`FlexibleModelMultipleChoiceField` which handles being able
    to select existing M2M relationships or create new ones, for example
    if a user wishes to create a new keyword not in the database.
    """
    def tearDown(self):
        Keyword.objects.all().delete()

    def test_check_values_filters_out_null_values(self):
        field = FlexibleModelMultipleChoiceField(
            klass=Keyword, to_field_name='text', required=False,
            queryset=Keyword.objects.none()
        )
        existing = field.clean(null_values_list)
        self.assertEqual(len(existing), 0)

    def test_new_values_detected(self):
        field = FlexibleModelMultipleChoiceField(
            klass=Keyword, to_field_name='text',
            queryset=Keyword.objects.none()
        )
        values = ['hello', 'world']
        qs = field.clean(values)
        self.assertEqual(len(qs), 2)
        self.assertIsNone(qs[0].pk)
        self.assertIsNone(qs[1].pk)

    def test_new_value_not_created_if_exists(self):
        field = FlexibleModelMultipleChoiceField(
            klass=Keyword, to_field_name='text',
            queryset=Keyword.objects.none()
        )
        kw = KeywordFactory(text='protein')
        qs = field.clean(['protein'])
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0], kw)


class TestFlexibleModelChoiceField(TestCase):
    """
    Tests the :class:`FlexibleModelChoiceField` which handles being able
    to select existing M2M relationships or create new ones, for example
    if a user wishes to create a new keyword not in the database.
    """
    def tearDown(self):
        Keyword.objects.all().delete()

    def test_check_values_filters_out_null_values(self):
        field = FlexibleModelChoiceField(
            klass=Keyword, to_field_name='text', required=False,
            queryset=Keyword.objects.none()
        )
        for value in null_values_list:
            v = field.clean(value)
            self.assertIsNone(v)

    def test_new_values_detected(self):
        field = FlexibleModelChoiceField(
            klass=Keyword, to_field_name='text',
            queryset=Keyword.objects.none()
        )
        values = 'hello world'
        v = field.clean(values)
        self.assertIsNone(v.pk)

    def test_new_value_not_created_if_exists(self):
        field = FlexibleModelChoiceField(
            klass=Keyword, to_field_name='text',
            queryset=Keyword.objects.none()
        )
        kw = KeywordFactory(text='protein')
        v = field.clean('protein')
        self.assertEqual(v, kw)
