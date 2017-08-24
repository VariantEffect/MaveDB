
from django.core.exceptions import ValidationError
from django.test import TestCase

from ..models import Keyword, ExternalAccession, TargetOrganism
from ..fields import ModelSelectMultipleField


class TestModelSelectMultipleField(TestCase):

    @staticmethod
    def create_n_instances(klass, text_ls):
        instances = []
        for text in set(text_ls):
            instances.append(klass.objects.create(text=text))
        return instances

    def test_can_instantiate(self):
        # test should not fail
        field = ModelSelectMultipleField(
            queryset=None,
            required=False,
            klass=Keyword,
            text_key="text"
        )

    def test_type_error_incorrect_class(self):
        with self.assertRaises(TypeError):
            field = ModelSelectMultipleField(
                queryset=None,
                required=False,
                klass=ModelSelectMultipleField,
                text_key="text"
            )

    def test_can_detect_valid_word(self):
        field = ModelSelectMultipleField(
            queryset=None,
            required=False,
            klass=Keyword,
            text_key="text"
        )
        self.assertTrue(field.is_word("a word"))
        self.assertTrue(field.is_word("aword"))
        self.assertTrue(field.is_word("1 1 1"))
        self.assertTrue(field.is_word("Word 1 1 1"))
        self.assertFalse(field.is_word("1"))
        self.assertFalse(field.is_word(" 1 "))
        self.assertFalse(field.is_word("1.3"))
        self.assertFalse(field.is_word("1.3 "))

    def test_can_clean_valid_pk_list(self):
        for klass in [Keyword, ExternalAccession, TargetOrganism]:
            instance = self.create_n_instances(
                klass, ['test1', 'test2', 'test3']
            )
            field = ModelSelectMultipleField(
                queryset=None,
                required=False,
                klass=klass,
                text_key="text"
            )
            field.queryset = klass.objects.all()
            values = [str(kw.pk) for kw in instance]
            qs = field.clean(values)
            self.assertEqual(qs.count(), 3)
            self.assertEqual(len(field.new_instances), 0)
            self.assertEqual(klass.objects.count(), 3)

    def test_error_invalid_pk_supplied(self):
        for klass in [Keyword, ExternalAccession, TargetOrganism]:
            instances = self.create_n_instances(
                klass, ['test1', 'test2', 'test3']
            )
            field = ModelSelectMultipleField(
                queryset=None,
                required=False,
                klass=klass,
                text_key="text"
            )
            field.queryset = klass.objects.all()
            values = [str(kw.pk) for kw in instances] + ['99', '100']
            with self.assertRaises(ValidationError):
                field.clean(values)

    def test_invalid_pk_float_input(self):
        for klass in [Keyword, ExternalAccession, TargetOrganism]:
            field = ModelSelectMultipleField(
                queryset=None,
                required=False,
                klass=klass,
                text_key="text"
            )
            field.queryset = klass.objects.all()
            values = ["1.0"]
            with self.assertRaises(ValidationError):
                field.clean(values)

    def test_new_instances_created_if_supplied_as_word(self):
        for klass in [Keyword, ExternalAccession, TargetOrganism]:
            instances = self.create_n_instances(
                klass, ['test1', 'test2', 'test3']
            )
            field = ModelSelectMultipleField(
                queryset=None,
                required=False,
                klass=klass,
                text_key="text"
            )
            field.queryset = klass.objects.all()
            values = [str(kw.pk) for kw in instances] + ['test4', 'test5']
            qs = field.clean(values)
            self.assertEqual(qs.count(), 3)
            self.assertEqual(len(field.new_instances), 2)

    def test_duplicate_new_instances_not_created(self):
        for klass in [Keyword, ExternalAccession, TargetOrganism]:
            instances = self.create_n_instances(
                klass, ['test1', 'test2', 'test3']
            )
            field = ModelSelectMultipleField(
                queryset=None,
                required=False,
                klass=klass,
                text_key="text"
            )
            field.queryset = klass.objects.all()
            values = [str(kw.pk) for kw in instances] + ['test4', 'test4']
            qs = field.clean(values)
            self.assertEqual(qs.count(), 3)
            self.assertEqual(len(field.new_instances), 1)

    def test_can_handle_duplicate_selection(self):
        for klass in [Keyword, ExternalAccession, TargetOrganism]:
            instances = self.create_n_instances(
                klass, ['test1', 'test2', 'test3']
            )
            field = ModelSelectMultipleField(
                queryset=None,
                required=False,
                klass=klass,
                text_key="text"
            )
            field.queryset = klass.objects.all()
            values = [instances[0].pk] * 3
            qs = field.clean(values)
            self.assertEqual(qs.count(), 1)
            self.assertEqual(len(field.new_instances), 0)

    def test_can_create_selection_with_only_new_entries(self):
        for klass in [Keyword, ExternalAccession, TargetOrganism]:
            field = ModelSelectMultipleField(
                queryset=None,
                required=False,
                klass=klass,
                text_key="text"
            )
            field.queryset = klass.objects.all()
            values = ['test1', 'test2', 'test3']
            qs = field.clean(values)
            self.assertEqual(qs.count(), 0)
            self.assertEqual(len(field.new_instances), 3)

    def test_existing_text_not_added_to_new_instances(self):
        for klass in [Keyword, ExternalAccession, TargetOrganism]:
            instances = self.create_n_instances(
                klass, ['test1', 'test2', 'test3']
            )
            field = ModelSelectMultipleField(
                queryset=None,
                required=False,
                klass=klass,
                text_key="text"
            )
            field.queryset = klass.objects.all()
            values = ["test1", "test4"]
            qs = field.clean(values)
            self.assertEqual(len(field.new_instances), 1)

    def test_blank_input_ignored(self):
        for klass in [Keyword, ExternalAccession, TargetOrganism]:
            instances = self.create_n_instances(
                klass, ['test1', 'test2', 'test3']
            )
            field = ModelSelectMultipleField(
                queryset=None,
                required=False,
                klass=klass,
                text_key="text"
            )
            field.queryset = klass.objects.all()
            values = ['']
            qs = field.clean(values)
            self.assertEqual(len(field.new_instances), 0)
