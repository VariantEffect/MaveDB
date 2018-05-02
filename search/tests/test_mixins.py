from django.test import TestCase

from ..mixins import FilterMixin

from metadata.models import PubmedIdentifier
from metadata.factories import PubmedIdentifierFactory

from dataset.models.experimentset import ExperimentSet
from dataset.factories import ExperimentSetFactory
from dataset.mixins import DatasetModelSearchMixin


class TestFilterMixin(TestCase):

    def test_list_to_or_q_makes_OR_Q(self):
        filter_ = FilterMixin()
        obj1 = ExperimentSetFactory(title='hello')
        obj2 = ExperimentSetFactory(title='world')
        obj3 = ExperimentSetFactory(title='this and that')

        q = filter_.list_to_or_q(
            values=['hello', 'world'],
            field_name='title',
            filter_type='icontains'
        )

        result = ExperimentSet.objects.filter(q)
        self.assertEqual(result.count(), 2)
        self.assertIn(obj1, result)
        self.assertIn(obj2, result)
        self.assertNotIn(obj3, result)

    def test_list_to_and_q_makes_AND_Q(self):
        filter_ = FilterMixin()
        obj1 = ExperimentSetFactory(title='this')
        obj2 = ExperimentSetFactory(title='that')
        obj3 = ExperimentSetFactory(title='this and that')

        q = filter_.list_to_and_q(
            values=['this', 'that'],
            field_name='title',
            filter_type='icontains'
        )

        result = ExperimentSet.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertNotIn(obj1, result)
        self.assertNotIn(obj2, result)
        self.assertIn(obj3, result)

    def test_value_to_q(self):
        filter_ = FilterMixin()
        obj1 = ExperimentSetFactory(title='hello')
        obj2 = ExperimentSetFactory(title='world')

        q = filter_.value_to_q(
            value='hello',
            field_name='title',
            filter_type='icontains'
        )

        result = ExperimentSet.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_join_Qs_with_OR(self):
        filter_ = FilterMixin()
        obj1 = ExperimentSetFactory(title='hello')
        obj2 = ExperimentSetFactory(title='world')
        obj3 = ExperimentSetFactory(title='this and that')
        obj4 = ExperimentSetFactory(title='this')

        q1 = filter_.list_to_and_q(
            values=['this', 'that'],
            field_name='title',
            filter_type='icontains'
        )
        q2 = filter_.list_to_or_q(
            values=['hello', 'world'],
            field_name='title',
            filter_type='icontains'
        )
        q = filter_.or_join_qs([q1, q2])

        result = ExperimentSet.objects.filter(q)
        self.assertEqual(result.count(), 3)
        self.assertIn(obj1, result)
        self.assertIn(obj2, result)
        self.assertIn(obj3, result)
        self.assertNotIn(obj4, result)

    def test_can_join_Qs_with_AND(self):
        filter_ = FilterMixin()
        obj1 = ExperimentSetFactory(title='hello')
        obj2 = ExperimentSetFactory(title='world')
        obj3 = ExperimentSetFactory(title='this and that')
        obj4 = ExperimentSetFactory(title='this and that and hello')

        q1 = filter_.list_to_and_q(
            values=['this', 'that'],
            field_name='title',
            filter_type='icontains'
        )
        q2 = filter_.list_to_or_q(
            values=['hello', 'world'],
            field_name='title',
            filter_type='icontains'
        )
        q = filter_.and_join_qs([q1, q2])

        result = ExperimentSet.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertNotIn(obj1, result)
        self.assertNotIn(obj2, result)
        self.assertNotIn(obj3, result)
        self.assertIn(obj4, result)

    def test_search_to_q_correctly_delegates_list_join(self):
        filter_ = FilterMixin()
        obj1 = ExperimentSetFactory(title='hello')
        obj2 = ExperimentSetFactory(title='world')
        obj3 = ExperimentSetFactory(title='Hello world')
        obj4 = ExperimentSetFactory()

        q = filter_.search_to_q(
            value=['hello', 'world'],
            field_name='title',
            filter_type='icontains',
            join='or'
        )

        result = ExperimentSet.objects.filter(q)
        self.assertEqual(result.count(), 3)
        self.assertIn(obj1, result)
        self.assertIn(obj2, result)
        self.assertIn(obj3, result)
        self.assertNotIn(obj4, result)

        q = filter_.search_to_q(
            value=['hello', 'world'],
            field_name='title',
            filter_type='icontains',
            join='and'
        )

        result = ExperimentSet.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertNotIn(obj1, result)
        self.assertNotIn(obj2, result)
        self.assertIn(obj3, result)
        self.assertNotIn(obj4, result)

    def test_search_to_q_returns_empty_q_in_input_is_empty(self):
        filter_ = FilterMixin()
        _ = ExperimentSetFactory()
        q = filter_.search_to_q(
            value=[],
            field_name='title',
            filter_type='icontains',
            join='or'
        )
        self.assertEqual(len(q), 0)
        self.assertEqual(ExperimentSet.objects.filter(q).count(), 1)

    def test_search_to_q_returns_single_q_for_single_element_list(self):
        filter_ = FilterMixin()
        obj1 = ExperimentSetFactory(title='hello')
        obj2 = ExperimentSetFactory(title='world')

        q = filter_.search_to_q(
            value=['hello'],
            field_name='title',
            filter_type='icontains'
        )

        result = ExperimentSet.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertEqual(len(q), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_join_funcs_filter_empty_qs(self):
        filter_ = FilterMixin()

        q1 = filter_.value_to_q(
            value='hello',
            field_name='title',
            filter_type='icontains'
        )
        q2 = filter_.list_to_or_q(
            values=[],
            field_name='title',
            filter_type='icontains'
        )

        result_or = filter_.or_join_qs([q1, q2])
        result_and = filter_.and_join_qs([q1, q2])

        self.assertEqual(len(result_or), 1)
        self.assertEqual(len(result_and), 1)


class TestSearchMixin(TestCase):

    def test_can_search_multiple_fields_with_OR(self):
        searcher = DatasetModelSearchMixin()

        obj1 = ExperimentSetFactory(title='hello')
        obj2 = ExperimentSetFactory(title='world')
        obj3 = ExperimentSetFactory(title='foo bar')
        PubmedIdentifier.objects.all().delete()

        pm = PubmedIdentifierFactory()
        obj2.pubmed_ids.add(pm)

        q = searcher.search_all(
            value_or_dict={"title": 'hello', 'pubmed': pm.identifier},
            join_func=searcher.or_join_qs
        )
        result = ExperimentSet.objects.filter(q)
        self.assertEqual(result.count(), 2)
        self.assertIn(obj1, result)
        self.assertIn(obj2, result)
        self.assertNotIn(obj3, result)

    def test_can_search_multiple_fields_with_AND(self):
        searcher = DatasetModelSearchMixin()

        obj1 = ExperimentSetFactory(title='hello')
        obj2 = ExperimentSetFactory(title='hello')
        obj3 = ExperimentSetFactory(title='foo bar')
        PubmedIdentifier.objects.all().delete()

        pm = PubmedIdentifierFactory()
        obj2.pubmed_ids.add(pm)

        q = searcher.search_all(
            value_or_dict={"title": 'hello', 'pubmed': pm.identifier},
            join_func=searcher.and_join_qs
        )
        result = ExperimentSet.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertNotIn(obj1, result)
        self.assertIn(obj2, result)
        self.assertNotIn(obj3, result)

    def test_empty_q_returns_all(self):
        searcher = DatasetModelSearchMixin()
        _ = ExperimentSetFactory(title='hello')
        _ = ExperimentSetFactory(title='hello')
        _ = ExperimentSetFactory(title='foo bar')

        q = searcher.search_all(
            value_or_dict={},
            join_func=searcher.and_join_qs
        )
        result = ExperimentSet.objects.filter(q)
        self.assertEqual(result.count(), 3)
        self.assertEqual(len(q), 0)

    def test_uknown_field_returns_empty_qs(self):
        searcher = DatasetModelSearchMixin()
        _ = ExperimentSetFactory(title='hello')
        _ = ExperimentSetFactory(title='hello')
        _ = ExperimentSetFactory(title='foo bar')

        q = searcher.search_all(
            value_or_dict={'unknown': 1},
            join_func=searcher.and_join_qs
        )
        result = ExperimentSet.objects.filter(q)
        self.assertEqual(result.count(), 3)
        self.assertEqual(len(q), 0)

    def test_string_search_searches_all_fields(self):
        searcher = DatasetModelSearchMixin()

        obj1 = ExperimentSetFactory(title='hello')
        obj2 = ExperimentSetFactory(short_description="hello")
        obj3 = ExperimentSetFactory(title='foo bar')

        q = searcher.search_all(
            value_or_dict='Hello',
            join_func=searcher.or_join_qs
        )
        result = ExperimentSet.objects.filter(q)
        self.assertEqual(result.count(), 2)
        self.assertIn(obj1, result)
        self.assertIn(obj2, result)
        self.assertNotIn(obj3, result)
