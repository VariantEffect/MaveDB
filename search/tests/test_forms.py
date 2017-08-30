from django.core.urlresolvers import reverse_lazy
from django.test import TestCase, RequestFactory

from main.models import Keyword, ExternalAccession, TargetOrganism
from experiment.models import Experiment
from scoreset.models import ScoreSet

from ..forms import SearchForm


class TestSearchForm(TestCase):

    def setUp(self):
        self.kw_1 = Keyword.objects.create(text="kw_1")
        self.kw_2 = Keyword.objects.create(text="kw_2")
        self.kw_3 = Keyword.objects.create(text="kw_3")
        self.ext_accession_1 = ExternalAccession.objects.create(text="ea_1")
        self.ext_accession_2 = ExternalAccession.objects.create(text="ea_2")
        self.ext_accession_3 = ExternalAccession.objects.create(text="ea_3")
        self.target_org_1 = TargetOrganism.objects.create(text="to_1")
        self.target_org_2 = TargetOrganism.objects.create(text="to_2")
        self.target_org_3 = TargetOrganism.objects.create(text="to_3")
        self.target_1 = "experiment_1"
        self.target_2 = "experiment_2"
        self.exp_1 = Experiment.objects.create(
            target=self.target_1, wt_sequence='atcg'
        )
        self.exp_2 = Experiment.objects.create(
            target=self.target_2, wt_sequence='atcg'
        )

    def test_can_create_form_from_data(self):
        form = SearchForm(data={})
        self.assertTrue(form.is_valid())

    def test_form_splits_by_comma(self):
        # All fields use the same `parse_query` method so only need
        # to test one field
        form = SearchForm(
            data={"accession": "one,two"})
        form.is_valid()
        self.assertEqual(
            sorted(form.cleaned_data.get("accession")),
            ['one', 'two']
        )

    def test_form_doesnt_split_quoted_text(self):
        # All fields use the same `parse_query` method so only need
        # to test one field
        form = SearchForm(data={"accession": "one,two,'three,four'"})
        form.is_valid()
        self.assertEqual(
            sorted(form.cleaned_data.get("accession")),
            sorted(['one', 'two', 'three,four'])
        )
        form = SearchForm(data={"accession": 'one,two,"three,four"'})
        form.is_valid()
        self.assertEqual(
            sorted(form.cleaned_data.get("accession")),
            sorted(['one', 'two', 'three,four'])
        )

    def test_can_search_experiment_by_keywords(self):
        key = 'keywords'
        self.exp_1.keywords.add(self.kw_1)
        form = SearchForm(data={key: '{}'.format(self.kw_1.text)})
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 1)
        self.assertEqual(self.exp_1, instances[0])

    def test_search_experiment_by_keyword_returns_empty_qs(self):
        key = 'keywords'
        form = SearchForm(data={key: '{},{}'.format(
            self.kw_2.text, self.kw_3.text)
        })
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 0)

    def test_experiment_keyword_search_can_return_multiple_results(self):
        key = 'keywords'
        self.exp_1.keywords.add(self.kw_1)
        self.exp_2.keywords.add(self.kw_2)
        form = SearchForm(data={key: '{},{}'.format(
            self.kw_1.text, self.kw_2)
        })
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 2)
        self.assertEqual(self.exp_1, instances[0])
        self.assertEqual(self.exp_2, instances[1])

    def test_experiment_keyword_search_is_case_insensitive(self):
        key = 'keywords'
        self.exp_1.keywords.add(self.kw_1)
        form = SearchForm(data={key: '{}'.format(self.kw_1.text.upper())})
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 1)
        self.assertEqual(self.exp_1, instances[0])
