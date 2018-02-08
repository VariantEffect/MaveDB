from django.core.urlresolvers import reverse_lazy
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

from main.models import Keyword, ExternalAccession, TargetOrganism
from experiment.models import Experiment
from scoreset.models import ScoreSet
from accounts.permissions import assign_user_as_instance_admin

from ..forms import SearchForm

User = get_user_model()


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
        self.target_3 = "experiment_3"
        self.exp_1 = Experiment.objects.create(
            target=self.target_1, wt_sequence='atcg'
        )
        self.exp_2 = Experiment.objects.create(
            target=self.target_2, wt_sequence='atcg'
        )
        self.exp_3 = Experiment.objects.create(
            target=self.target_3, wt_sequence='atcg'
        )

    def test_can_create_form_from_data(self):
        form = SearchForm(data={})
        self.assertTrue(form.is_valid())

    def test_can_parse_search_all_get_request(self):
        form = SearchForm(data={"search_all": "one,two,'three,four'"})
        self.assertTrue(form.is_valid())
        self.assertEqual(
            sorted(form.cleaned_data.get("search_all")),
            sorted(['one', 'two', 'three,four'])
        )

    def test_form_splits_by_comma(self):
        # All fields use the same `parse_query` method so only need
        # to test one field
        form = SearchForm(
            data={"accessions": "one,two"})
        form.is_valid()
        self.assertEqual(
            sorted(form.cleaned_data.get("accessions")),
            ['one', 'two']
        )

    def test_form_doesnt_split_quoted_text(self):
        # All fields use the same `parse_query` method so only need
        # to test one field
        form = SearchForm(data={"accessions": "one,two,'three,four'"})
        form.is_valid()
        self.assertEqual(
            sorted(form.cleaned_data.get("accessions")),
            sorted(['one', 'two', 'three,four'])
        )
        form = SearchForm(data={"accessions": 'one,two,"three,four"'})
        form.is_valid()
        self.assertEqual(
            sorted(form.cleaned_data.get("accessions")),
            sorted(['one', 'two', 'three,four'])
        )

    def test_search_all_can_find_all_matches(self):
        key = 'search_all'
        self.exp_1.keywords.add(self.kw_1)
        self.exp_2.abstract = "dna repair"
        self.exp_2.save()
        form = SearchForm(data={key: '{},dna repair,a thing'.format(
            self.kw_1.text)
        })
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 2)

    def test_search_all_ignored_when_other_fields_present(self):
        self.exp_1.keywords.add(self.kw_1)
        form = SearchForm(data={
            'search_all': 'dna repair,a thing',
            'keywords': self.kw_1.text
        })
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 1)
        self.assertEqual(instances[0], self.exp_1)

    ###
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

    ###
    def test_can_search_experiment_by_ext_accession(self):
        key = 'ext_accessions'
        self.exp_1.external_accessions.add(self.ext_accession_1)
        form = SearchForm(data={key: '{}'.format(self.ext_accession_1.text)})
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 1)
        self.assertEqual(self.exp_1, instances[0])

    def test_search_experiment_by_ext_accession_returns_empty_qs(self):
        key = 'ext_accessions'
        form = SearchForm(data={key: '{},{}'.format(
            self.ext_accession_2.text, self.ext_accession_3.text)
        })
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 0)

    def test_experiment_ext_accession_search_can_return_multiple_results(self):
        key = 'ext_accessions'
        self.exp_1.external_accessions.add(self.ext_accession_1)
        self.exp_2.external_accessions.add(self.ext_accession_2)
        form = SearchForm(data={key: '{},{}'.format(
            self.ext_accession_1.text, self.ext_accession_2.text)
        })
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 2)
        self.assertEqual(self.exp_1, instances[0])
        self.assertEqual(self.exp_2, instances[1])

    def test_experiment_ext_accession_search_is_case_insensitive(self):
        key = 'ext_accessions'
        self.exp_1.external_accessions.add(self.ext_accession_1)
        form = SearchForm(data={key: '{}'.format(
            self.ext_accession_1.text.upper())}
        )
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 1)
        self.assertEqual(self.exp_1, instances[0])

    ###
    def test_can_search_experiment_by_target(self):
        key = 'targets'
        form = SearchForm(data={key: self.target_1})
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 1)
        self.assertEqual(self.exp_1, instances[0])

    def test_search_experiment_by_target_returns_empty_qs(self):
        key = 'targets'
        form = SearchForm(data={key: 'not a target'})
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 0)

    def test_experiment_target_search_can_return_multiple_results(self):
        key = 'targets'
        form = SearchForm(data={key: '{},{}'.format(
            self.target_1, self.target_2)
        })
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 2)
        self.assertEqual(self.exp_1, instances[0])
        self.assertEqual(self.exp_2, instances[1])

    def test_experiment_target_search_is_case_insensitive(self):
        key = 'targets'
        form = SearchForm(data={key: '{}'.format(
            self.target_1.upper())
        })
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 1)
        self.assertEqual(self.exp_1, instances[0])

    ###
    def test_can_search_experiment_by_target_organism(self):
        key = 'target_organisms'
        self.exp_1.target_organism.add(self.target_org_1)
        form = SearchForm(data={key: '{}'.format(self.target_org_1.text)})
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 1)
        self.assertEqual(self.exp_1, instances[0])

    def test_search_experiment_by_target_organism_returns_empty_qs(self):
        key = 'target_organisms'
        form = SearchForm(data={key: '{},{}'.format(
            self.target_org_2.text, self.target_org_3.text)
        })
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 0)

    def test_experiment_target_org_search_can_return_multiple_results(self):
        key = 'target_organisms'
        self.exp_1.target_organism.add(self.target_org_1)
        self.exp_2.target_organism.add(self.target_org_2)
        form = SearchForm(data={key: '{},{}'.format(
            self.target_org_1.text, self.target_org_2.text)
        })
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 2)
        self.assertEqual(self.exp_1, instances[0])
        self.assertEqual(self.exp_2, instances[1])

    def test_experiment_target_organism_search_is_case_insensitive(self):
        key = 'target_organisms'
        self.exp_1.target_organism.add(self.target_org_1)
        form = SearchForm(data={key: '{}'.format(
            self.target_org_1.text.upper())}
        )
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 1)
        self.assertEqual(self.exp_1, instances[0])

    ###
    def test_can_search_experiment_by_metadata(self):
        key = 'metadata'
        self.exp_1.abstract = "DNA repair"
        self.exp_2.method_desc = "DNA repair"
        self.exp_1.save()
        self.exp_2.save()
        form = SearchForm(data={key: "DNA repair"})
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 2)

    def test_search_experiment_by_metadata_returns_empty_qs(self):
        key = 'metadata'
        form = SearchForm(data={key: 'should not find a hit'})
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 0)

    def test_experiment_metadata_search_can_return_multiple_results(self):
        key = 'metadata'
        self.exp_1.abstract = "DNA repair"
        self.exp_2.method_desc = "the great mitochondria war"
        self.exp_1.save()
        self.exp_2.save()
        form = SearchForm(data={key: 'DNA repair,the great mitochondria war'})
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 2)
        self.assertTrue(self.exp_1 in instances)
        self.assertTrue(self.exp_2 in instances)

    def test_experiment_metadata_search_is_case_insensitive(self):
        key = 'metadata'
        self.exp_1.abstract = "DNA repair"
        self.exp_1.save()
        form = SearchForm(data={key: 'DNA REPAIR'})
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 1)
        self.assertEqual(self.exp_1, instances[0])

    ###
    def test_can_search_experiment_by_author_name(self):
        key = 'authors'
        alice = User.objects.create(
            username="0000", first_name="Alice", last_name="Bob"
        )
        assign_user_as_instance_admin(alice, self.exp_1)

        form = SearchForm(data={key: 'alice'})
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 1)
        self.assertEqual(self.exp_1, instances[0])

    def test_can_search_experiment_by_author_orcid(self):
        key = 'authors'
        alice = User.objects.create(
            username="0000"
        )
        assign_user_as_instance_admin(alice, self.exp_1)
        form = SearchForm(data={key: '0000'})
        form.is_valid()
        instances = form.query_experiments()
        self.assertEqual(instances.count(), 1)
        self.assertEqual(self.exp_1, instances[0])
