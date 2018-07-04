import json

from django.test import TestCase, RequestFactory, mock
from django.http import Http404

from core.utilities.pandoc import convert_md_to_html

from accounts.factories import UserFactory, AnonymousUserFactory

from genome.factories import ReferenceGenomeFactory
from metadata.factories import (
    UniprotIdentifierFactory, RefseqIdentifierFactory,
    EnsemblIdentifierFactory
)

from main.models import Licence

from ..models.experiment import Experiment
from ..models.scoreset import ScoreSet
from ..factories import ExperimentWithScoresetFactory, ScoreSetWithTargetFactory
from ..forms.scoreset import ScoreSetForm, ScoreSetEditForm
from ..forms.experiment import ExperimentForm, ExperimentEditForm
from ..mixins import (
    PrivateDatasetFilterMixin, ScoreSetAjaxMixin, MultiFormMixin,
    DatasetUrnMixin, DatasetPermissionMixin, DataSetAjaxMixin,
    ExperimentFilterMixin, ScoreSetFilterMixin
)


class TestPrivateDatasetFilterMixin(TestCase):
    
    class Driver(PrivateDatasetFilterMixin):
        def __init__(self, request):
            self.request = request
        
    def setUp(self):
        self.factory = RequestFactory()
        
    def test_separates_private_viewable(self):
        request = self.factory.get('/')
        request.user = UserFactory()
        driver = self.Driver(request)
        
        i1 = ExperimentWithScoresetFactory() # type: Experiment
        i2 = ExperimentWithScoresetFactory() # type: Experiment
        i1.add_viewers(request.user)
        
        public, private = driver.filter_and_split_instances([i1, i2])
        self.assertIn(i1, private)
        self.assertNotIn(i2, private)
        self.assertNotIn(i1, public)
        self.assertNotIn(i2, public)
        
    def test_separates_public(self):
        request = self.factory.get('/')
        request.user = UserFactory()
        driver = self.Driver(request)
    
        i1 = ExperimentWithScoresetFactory()  # type: Experiment
        i2 = ExperimentWithScoresetFactory()  # type: Experiment
        i1.publish()
        i1.save()
    
        public, private = driver.filter_and_split_instances([i1, i2])
        self.assertNotIn(i1, private)
        self.assertNotIn(i2, private)
        self.assertIn(i1, public)
        self.assertNotIn(i2, public)
        
        
class TestDataSetAjaxMixin(TestCase):
    """Testing pandoc conversion of abstract and method blobs."""
    def setUp(self):
        self.factory = RequestFactory()
        
    def test_converts_abstract_to_md(self):
        request = self.factory.get(
            path='/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            data={'abstractText': "# Hello world"}
        )
        driver = DataSetAjaxMixin()
        response = json.loads(driver.get_ajax(request).content.decode())
        self.assertEqual(
            response['abstractText'],
            convert_md_to_html("# Hello world")
        )
        
    def test_converts_method_to_md(self):
        request = self.factory.get(
            path='/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            data={'methodText': "# Hello world"}
        )
        driver = DataSetAjaxMixin()
        response = json.loads(driver.get_ajax(request).content.decode())
        self.assertEqual(
            response['methodText'],
            convert_md_to_html("# Hello world")
        )
        
    def test_empty_dict_if_no_GET_param_found(self):
        request = self.factory.get(
            path='/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            data={}
        )
        driver = DataSetAjaxMixin()
        response = json.loads(driver.get_ajax(request).content.decode())
        self.assertEqual(response, {})


class TestScoreSetAjaxMixin(TestCase):
    """Testing ajax response for getting target gene and experiment scoresets."""
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_can_get_target(self):
        driver = ScoreSetAjaxMixin()
        scoreset = ScoreSetWithTargetFactory()
        request = self.factory.get(
            path='/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            data={'targetId': scoreset.target.pk}
        )
        response = json.loads(driver.get_ajax(request).content.decode())
        self.assertEqual(
            response['name'], scoreset.target.name)
        self.assertEqual(
            response['genome'],
            scoreset.target.reference_maps.first().genome.pk
        )
        
    def test_lists_editable_scoresets(self):
        driver = ScoreSetAjaxMixin()
        
        user = UserFactory()
        experiment = ExperimentWithScoresetFactory()
        sc1 = experiment.scoresets.first() # type: ScoreSet
        sc2 = ScoreSetWithTargetFactory(experiment=experiment) # type: ScoreSet
        sc3 = ScoreSetWithTargetFactory(experiment=experiment)  # type: ScoreSet
        sc4 = ScoreSetWithTargetFactory(experiment=experiment)  # type: ScoreSet
        
        # Viewable since user has edit permission and is not private
        sc1.publish()
        sc1.add_editors(user)
        sc1.save(save_parents=True)
        
        # Is private so should not be viewable
        sc2.add_editors(user)
        
        # No edit permission so not viewable
        sc4.publish()
        sc4.save(save_parents=True)
        
        request = self.factory.get(
            path='/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            data={'experiment': experiment.pk}
        )
        request.user = user
        response = json.loads(driver.get_ajax(request).content.decode())
        self.assertIn([sc1.pk, sc1.urn], response['scoresets'])
        self.assertNotIn([sc2.pk, sc2.urn], response['scoresets'])
        self.assertNotIn([sc3.pk, sc3.urn], response['scoresets'])
        self.assertNotIn([sc4.pk, sc4.urn], response['scoresets'])


class TestDatasetPermissionMixin(TestCase):
    """Testing permission mixin `has_permission` override."""
    
    class Driver(DatasetPermissionMixin):
        def __init__(self, instance, request):
            self.instance = instance
            self.request = request
        
        def get_object(self):
            return self.instance
        
    def setUp(self):
        self.factory = RequestFactory()
    
    # Manage
    def test_false_private_and_no_manage_permission(self):
        scoreset = ScoreSetWithTargetFactory() # type: ScoreSet
        request = self.factory.get('/')
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        driver.permission_required = 'dataset.can_manage'
        self.assertFalse(driver.has_permission())
        
    def test_true_private_and_mange_permssion_match(self):
        scoreset = ScoreSetWithTargetFactory() # type: ScoreSet
        request = self.factory.get('/')
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)
        
        scoreset.add_administrators(request.user)
        driver.permission_required = 'dataset.can_manage'
        self.assertTrue(driver.has_permission())

    def test_false_public_and_no_manage_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get('/')
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)
    
        scoreset.publish()
        driver.permission_required = 'dataset.can_manage'
        self.assertFalse(driver.has_permission())

    def test_true_public_and_manage_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get('/')
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)
    
        scoreset.add_administrators(request.user)
        scoreset.publish()
        driver.permission_required = 'dataset.can_manage'
        self.assertTrue(driver.has_permission())

    # Edit
    def test_false_private_and_no_edit_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get('/')
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)

        driver.permission_required = 'dataset.can_edit'
        self.assertFalse(driver.has_permission())

    def test_true_private_and_edit_permssion_match(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get('/')
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)
    
        scoreset.add_editors(request.user)
        driver.permission_required = 'dataset.can_edit'
        self.assertTrue(driver.has_permission())
        
    def test_false_public_and_no_edit_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get('/')
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)
    
        scoreset.publish()
        driver.permission_required = 'dataset.can_edit'
        self.assertFalse(driver.has_permission())

    def test_true_public_and_edit_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get('/')
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)
    
        scoreset.add_editors(request.user)
        scoreset.publish()
        driver.permission_required = 'dataset.can_edit'
        self.assertTrue(driver.has_permission())
    
    # View
    def test_false_private_and_no_view_permission(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get('/')
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)
    
        driver.permission_required = 'dataset.can_view'
        self.assertFalse(driver.has_permission())

    def test_true_private_and_view_permssion_match(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get('/')
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)
    
        scoreset.add_viewers(request.user)
        driver.permission_required = 'dataset.can_view'
        self.assertTrue(driver.has_permission())

    def test_true_public_instance_view(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        scoreset.publish()
        request = self.factory.get('/')
        request.user = UserFactory()
        driver = self.Driver(instance=scoreset, request=request)
    
        self.assertTrue(driver.has_permission())
        
    # Anon
    def test_false_anon(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get('/')
        request.user = AnonymousUserFactory()
        driver = self.Driver(instance=scoreset, request=request)
        
        self.assertFalse(driver.has_permission())

    def test_false_public_no_edit_permission_anon(self):
        scoreset = ScoreSetWithTargetFactory() # type: ScoreSet
        request = self.factory.get('/')
        request.user = AnonymousUserFactory()
        driver = self.Driver(instance=scoreset, request=request)
        
        driver.permission_required = 'dataset.can_edit'
        self.assertFalse(driver.has_permission())
    
    def test_false_public_no_manage_permission_anon(self):
        scoreset = ScoreSetWithTargetFactory()  # type: ScoreSet
        request = self.factory.get('/')
        request.user = AnonymousUserFactory()
        driver = self.Driver(instance=scoreset, request=request)
    
        driver.permission_required = 'dataset.can_manage'
        self.assertFalse(driver.has_permission())


class TestDatasetUrnMixin(TestCase):
    """Tests the `get_object` method overriden by `DatasetUrnMixin"""
    class Driver(DatasetUrnMixin):
        def __init__(self, kwargs):
            self.kwargs = kwargs
            self.model = None
            self.model_class = None
            
    def test_404_not_found(self):
        driver = self.Driver(kwargs={'urn': None})
        driver.model = ScoreSet
        with self.assertRaises(Http404):
            driver.get_object()
            
    def test_can_get_object(self):
        scoreset = ScoreSetWithTargetFactory()
        driver = self.Driver(kwargs={'urn': scoreset.urn})
        driver.model = ScoreSet
        self.assertEqual(scoreset, driver.get_object())
    
    def test_fallsback_to_model_class(self):
        scoreset = ScoreSetWithTargetFactory()
        driver = self.Driver(kwargs={'urn': scoreset.urn})
        driver.model_class = ScoreSet
        driver.__delattr__('model')
        driver.model_class = ScoreSet
        self.assertEqual(scoreset, driver.get_object())


class TestMultiFormMixin(TestCase):
    """Tests that custom form and kwarg methods are called as expected."""
    class Driver(MultiFormMixin):
        def __init__(self, request, user):
            self.request = request
            self.user = user
            
        def get_scoreset_form(self, form_class, **kwargs):
            return form_class(**kwargs)
        
        def get_scoreset_form_kwargs(self, key):
            return {'user': self.user, 'data': {}}
        
    def setUp(self):
        self.factory = RequestFactory()

    @mock.patch.object(Driver, 'get_scoreset_form_kwargs')
    @mock.patch.object(Driver, 'get_scoreset_form')
    def test_calls_scoreset_form_method(self, form_patch, kwarg_patch):
        user = UserFactory()
        request = self.factory.post('/', data={})
        request.user = user
        driver = self.Driver(request=request, user=user)
        driver.forms = {'scoreset': ScoreSetForm,}
        driver.get_forms()
        form_patch.assert_called()
        kwarg_patch.assert_called()

    @mock.patch.object(Driver, 'get_scoreset_form')
    def test_does_not_overwrite_user_in_kwargs(self, form_patch):
        request = self.factory.post('/')
        user1 = UserFactory()
        user2 = UserFactory()
        request.user = user2
        driver = self.Driver(request=request, user=user1)
        driver.forms = {'scoreset': ScoreSetForm, }
    
        driver.get_forms()
        self.assertEqual(form_patch.call_args[1]['user'], driver.user)

    @mock.patch.object(Driver, 'get_generic_form')
    def test_adds_missing_kwargs(self, form_patch):
        user = UserFactory()
        request = self.factory.post('/')
        request.user = user
        driver = self.Driver(request=request, user=user)
        driver.forms = {'experiment': ExperimentForm,}
        
        driver.get_forms()
        self.assertIn('files', form_patch.call_args[1])
        self.assertIn('data', form_patch.call_args[1])
        self.assertIn('instance', form_patch.call_args[1])
        self.assertIn('prefix', form_patch.call_args[1])
        self.assertIn('user', form_patch.call_args[1])
        
    @mock.patch.object(Driver, 'get_scoreset_form')
    def test_adds_form_prefix(self, form_patch):
        user = UserFactory()
        request = self.factory.post('/')
        request.user = user
        driver = self.Driver(request=request, user=user)
        driver.forms = {'scoreset': ScoreSetForm, }
        driver.prefixes = {'scoreset': 'foobar'}
        
        driver.get_forms()
        self.assertEqual(form_patch.call_args[1]['prefix'], 'foobar')

    @mock.patch.object(Driver, 'get_scoreset_form')
    def test_adds_form_instance(self, form_patch):
        user = UserFactory()
        request = self.factory.post('/')
        request.user = user
        driver = self.Driver(request=request, user=user)
        driver.forms = {'scoreset': ScoreSetForm, }
        
        scoreset = ScoreSetWithTargetFactory()
        setattr(driver, 'instance', scoreset)

        driver.get_forms()
        self.assertEqual(form_patch.call_args[1]['instance'], scoreset)

    @mock.patch.object(Driver, 'get_scoreset_form')
    def test_adds_user_instance(self, form_patch):
        user = UserFactory()
        request = self.factory.post('/')
        request.user = user
        driver = self.Driver(request=request, user=user)
        driver.forms = {'scoreset': ScoreSetForm, }
        
        driver.get_forms()
        self.assertEqual(form_patch.call_args[1]['user'], request.user)

    @mock.patch.object(Driver, 'get_generic_kwargs')
    @mock.patch.object(Driver, 'get_generic_form')
    def test_calls_generic_when_no_method_defined(self, form_patch, kwarg_patch):
        user = UserFactory()
        request = self.factory.post('/')
        request.user = user
        driver = self.Driver(request=request, user=user)
        driver.forms = {'experiment': ExperimentForm, }
        driver.get_forms()
        form_patch.assert_called()
        kwarg_patch.assert_called()


class TestExperimentSearchMixin(TestCase):
    """Test search fields implemented by `ExperimentSearchMixin."""
    def setUp(self):
        self.factory = ExperimentWithScoresetFactory
        self.searcher = ExperimentFilterMixin()
        self.model_class = Experiment

    def can_filter_by_keywords_in_scoresets(self):
        obj1 = self.factory()
        kw1_obj1 = obj1.keywords.first()
        kw1_obj1.text = 'Protein'
        kw1_obj1.save()

        scs1 = obj1.children.first()
        kw1 = scs1.keywords.first()
        kw1.text = 'Kinase'
        kw1.save()

        obj2 = self.factory()
        kw1_obj2 = obj2.keywords.first()
        kw1_obj2.text = 'Apple'
        kw1_obj2.save()

        scs2 = obj2.children.first()
        kw2 = scs2.keywords.first()
        kw2.text = 'Orange'
        kw2.save()

        q = self.searcher.search_all(
            value_or_dict={"keywords": kw1.text},
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_filter_singular_target(self):
        obj1 = self.factory()
        target1 = obj1.children.first().get_target()
        target1.name = 'JAK'
        target1.save()

        obj2 = self.factory()
        target2 = obj2.children.first().get_target()
        target2.name = 'STAT'
        target2.save()

        q = self.searcher.search_all(
            value_or_dict={"target": target1.get_name().lower()},
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_filter_multiple_targets(self):
        obj1 = self.factory()
        target1 = obj1.children.first().get_target()
        target1.name = 'JAK'
        target1.save()

        obj2 = self.factory()
        target2 = obj2.children.first().get_target()
        target2.name = 'MAP'
        target2.save()

        q = self.searcher.search_all(
            value_or_dict={"target": [
                target1.get_name(),
                target2.get_name(),
            ]},
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 2)
        self.assertIn(obj1, result)
        self.assertIn(obj2, result)

    def test_can_AND_search(self):
        obj1 = self.factory()
        target1 = obj1.children.first().get_target()
        target1.name = 'JAK'
        target1.save()

        obj2 = self.factory()
        target2 = obj2.children.first().get_target()
        target2.name = 'MAP'
        target2.save()

        obj3 = self.factory()
        target3 = obj3.children.first().get_target()
        target3.name = 'STAT'
        target3.save()

        q = self.searcher.search_all(
            value_or_dict={
                "target": [
                    target1.get_name(),
                    target2.get_name(),
                ],
                'urn': obj1.urn
            },
            join_func=self.searcher.and_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)
        self.assertNotIn(obj3, result)

    def test_can_OR_search(self):
        obj1 = self.factory()
        target1 = obj1.children.first().get_target()
        target1.name = 'JAK'
        target1.save()

        obj2 = self.factory()
        target2 = obj2.children.first().get_target()
        target2.name = 'MAP'
        target2.save()

        obj3 = self.factory()
        target3 = obj3.children.first().get_target()
        target3.name = 'STAT'
        target3.save()

        q = self.searcher.search_all(
            value_or_dict={
                "target": [
                    target2.get_name().lower(),
                ],
                'urn': obj1.urn
            },
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 2)
        self.assertIn(obj1, result)
        self.assertIn(obj2, result)
        self.assertNotIn(obj3, result)

    def test_can_search_by_organism(self):
        obj1 = self.factory()
        obj2 = self.factory()

        genome1 = obj1.children.first().get_target().\
            get_reference_genomes().first()
        genome1.species_name = 'Human'
        genome1.save()

        genome2 = obj2.children.first().get_target().\
            get_reference_genomes().first()
        genome2.species_name = 'Chimp'
        genome2.save()
        
        q = self.searcher.search_all(
            value_or_dict={
                "species": ["human"]
            },
            join_func=self.searcher.or_join_qs
        )

        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_by_genome_name(self):
        obj1 = self.factory()
        obj2 = self.factory()

        genome1 = obj1.children.first().get_target().\
            get_reference_genomes().first()
        genome1.short_name = 'Hg16'
        genome1.save()

        genome2 = obj2.children.first().get_target().\
            get_reference_genomes().first()
        genome2.short_name = 'Hg17'
        genome2.save()

        q = self.searcher.search_all(
            value_or_dict={'genome': 'hg16'},
            join_func=self.searcher.or_join_qs
        )

        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_by_genome_id(self):
        obj1 = self.factory()
        obj2 = self.factory()
        genome1 = obj1.scoresets.first().\
            get_target().get_reference_genomes().first()
        genome2 = obj2.scoresets.first().\
            get_target().get_reference_genomes().first()

        while genome1.get_identifier() == genome2.get_identifier():
            genome2 = ReferenceGenomeFactory()
            if genome1.get_identifier() != genome2.get_identifier():
                rm = obj2.scoresets.first().\
                        get_target().get_reference_maps().first()
                rm.genome = genome2
                rm.save()

        q = self.searcher.search_all(
            value_or_dict={'assembly': genome1.get_identifier()},
            join_func=self.searcher.or_join_qs
        )

        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_by_id(self):
        obj1 = self.factory()
        obj2 = self.factory()
        id_factories = [
            (UniprotIdentifierFactory, 'uniprot_id'),
            (RefseqIdentifierFactory, 'refseq_id'),
            (EnsemblIdentifierFactory, 'ensembl_id'),
        ]

        for factory, field in id_factories:
            id1 = factory()
            id2 = factory()
            while id1 == id2:
                id2 = factory()

            target1 = obj1.children.first().get_target()
            target2 = obj2.children.first().get_target()
            setattr(target1, field, id1)
            target1.save()
            setattr(target2, field, id2)
            target2.save()

            q = self.searcher.search_all(
                value_or_dict={field.replace('_id', ''): id1.identifier},
                join_func=self.searcher.or_join_qs
            )

            result = self.model_class.objects.filter(q)
            self.assertEqual(result.count(), 1)
            self.assertIn(obj1, result)
            self.assertNotIn(obj2, result)

    def test_can_search_by_licence_short_name(self):
        obj1 = self.factory()
        obj2 = self.factory()

        scs1 = obj1.scoresets.first()
        scs2 = obj2.scoresets.first()
        scs1.licence = Licence.get_cc0()
        scs2.licence = Licence.get_cc_by_nc_sa()
        scs1.save()
        scs2.save()

        q = self.searcher.search_all(
            value_or_dict={'licence': Licence.get_cc0().short_name},
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

        q = self.searcher.search_all(
            value_or_dict={'licence': Licence.get_cc_by_nc_sa().short_name},
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertNotIn(obj1, result)
        self.assertIn(obj2, result)

    def test_can_search_by_licence_long_name(self):
        obj1 = self.factory()
        obj2 = self.factory()

        scs1 = obj1.scoresets.first()
        scs2 = obj2.scoresets.first()
        scs1.licence = Licence.get_cc0()
        scs2.licence = Licence.get_cc_by_nc_sa()
        scs1.save()
        scs2.save()

        q = self.searcher.search_all(
            value_or_dict={'licence': Licence.get_cc0().long_name},
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

        q = self.searcher.search_all(
            value_or_dict={'licence': Licence.get_cc_by_nc_sa().long_name},
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertNotIn(obj1, result)
        self.assertIn(obj2, result)


class TestScoreSetSearchMixin(TestCase):
    """Test search fields implemented by `ScoreSetSearchMixin."""
    def setUp(self):
        self.factory = ScoreSetWithTargetFactory
        self.searcher = ScoreSetFilterMixin()
        self.model_class = ScoreSet

    def test_can_filter_singular_target(self):
        obj1 = self.factory()
        target1 = obj1.get_target()
        target1.name = 'JAK'
        target1.save()

        obj2 = self.factory()
        target2 = obj2.get_target()
        target2.name = 'MAP'
        target2.save()

        q = self.searcher.search_all(
            value_or_dict={"target": 'JAK'},
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_filter_multiple_targets(self):
        obj1 = self.factory()
        target1 = obj1.get_target()
        target1.name = 'JAK'
        target1.save()

        obj2 = self.factory()
        target2 = obj2.get_target()
        target2.name = 'MAP'
        target2.save()

        obj3 = self.factory()
        target3 = obj3.get_target()
        target3.name = 'STAT'
        target3.save()

        q = self.searcher.search_all(
            value_or_dict={"target": [
                target1.get_name(),
                target2.get_name(),
            ]},
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 2)
        self.assertIn(obj1, result)
        self.assertIn(obj2, result)
        self.assertNotIn(obj3, result)

    def test_can_AND_search(self):
        obj1 = self.factory()
        target1 = obj1.get_target()
        target1.name = 'JAK'
        target1.save()

        obj2 = self.factory()
        target2 = obj2.get_target()
        target2.name = 'MAP'
        target2.save()

        obj3 = self.factory()
        target3 = obj3.get_target()
        target3.name = 'STAT'
        target3.save()

        q = self.searcher.search_all(
            value_or_dict={
                "target": [
                    target1.get_name(),
                    target2.get_name(),
                ],
                'urn': obj1.urn
            },
            join_func=self.searcher.and_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)
        self.assertNotIn(obj3, result)

    def test_can_OR_search(self):
        obj1 = self.factory()
        target1 = obj1.get_target()
        target1.name = 'JAK'
        target1.save()

        obj2 = self.factory()
        target2 = obj2.get_target()
        target2.name = 'MAP'
        target2.save()

        obj3 = self.factory()
        target3 = obj3.get_target()
        target3.name = 'STAT'
        target3.save()

        q = self.searcher.search_all(
            value_or_dict={
                "target": [
                    target1.get_name(),
                    target2.get_name(),
                ],
                'urn': obj1.urn
            },
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 2)
        self.assertIn(obj1, result)
        self.assertIn(obj2, result)
        self.assertNotIn(obj3, result)

    def test_can_search_by_organism(self):
        obj1 = self.factory()
        obj2 = self.factory()

        genome1 = obj1.get_target().get_reference_genomes().first()
        genome1.species_name = 'Human'
        genome1.save()

        genome2 = obj2.get_target().get_reference_genomes().first()
        genome2.species_name = 'Chimp'
        genome2.save()

        q = self.searcher.search_all(
            value_or_dict={
                "species": ["human"]
            },
            join_func=self.searcher.or_join_qs
        )

        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_by_genome_name(self):
        obj1 = self.factory()
        obj2 = self.factory()

        genome1 = obj1.get_target().get_reference_genomes().first()
        genome1.short_name = 'Hg16'
        genome1.save()

        genome2 = obj2.get_target().get_reference_genomes().first()
        genome2.short_name = 'Hg17'
        genome2.save()

        q = self.searcher.search_all(
            value_or_dict={'genome': 'hg16'},
            join_func=self.searcher.or_join_qs
        )

        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_by_genome_id(self):
        obj1 = self.factory()
        obj2 = self.factory()
        genome1 = obj1.get_target().get_reference_genomes().first()
        genome2 = obj2.get_target().get_reference_genomes().first()

        while genome1.get_identifier() == genome2.get_identifier():
            genome2 = ReferenceGenomeFactory()
            if genome1.get_identifier() != genome2.get_identifier():
                rm = obj2.target.get_reference_maps().first()
                rm.genome = genome2
                rm.save()

        q = self.searcher.search_all(
            value_or_dict={'assembly': genome1.get_identifier()},
            join_func=self.searcher.or_join_qs
        )

        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

    def test_can_search_by_licence_short_name(self):
        obj1 = self.factory()
        obj2 = self.factory()
        obj1.licence = Licence.get_cc0()
        obj2.licence = Licence.get_cc_by_nc_sa()
        obj1.save()
        obj2.save()

        q = self.searcher.search_all(
            value_or_dict={'licence': Licence.get_cc0().short_name},
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

        q = self.searcher.search_all(
            value_or_dict={'licence': Licence.get_cc_by_nc_sa().short_name},
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertNotIn(obj1, result)
        self.assertIn(obj2, result)

    def test_can_search_by_licence_long_name(self):
        obj1 = self.factory()
        obj2 = self.factory()
        obj1.licence = Licence.get_cc0()
        obj2.licence = Licence.get_cc_by_nc_sa()
        obj1.save()
        obj2.save()

        q = self.searcher.search_all(
            value_or_dict={'licence': Licence.get_cc0().long_name},
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertIn(obj1, result)
        self.assertNotIn(obj2, result)

        q = self.searcher.search_all(
            value_or_dict={'licence': Licence.get_cc_by_nc_sa().long_name},
            join_func=self.searcher.or_join_qs
        )
        result = self.model_class.objects.filter(q)
        self.assertEqual(result.count(), 1)
        self.assertNotIn(obj1, result)
        self.assertIn(obj2, result)

    def test_can_search_by_external_id(self):
        obj1 = self.factory()
        obj2 = self.factory()
        id_factories = [
            (UniprotIdentifierFactory, 'uniprot_id'),
            (RefseqIdentifierFactory, 'refseq_id'),
            (EnsemblIdentifierFactory, 'ensembl_id'),
        ]

        for factory, field in id_factories:
            id1 = factory()
            id2 = factory()
            while id1 == id2:
                id2 = factory()

            target1 = obj1.get_target()
            target2 = obj2.get_target()
            setattr(target1, field, id1)
            target1.save()
            setattr(target2, field, id2)
            target2.save()

            q = self.searcher.search_all(
                value_or_dict={field.replace('_id', ''): id1.identifier},
                join_func=self.searcher.or_join_qs
            )

            result = self.model_class.objects.filter(q)
            self.assertEqual(result.count(), 1)
            self.assertIn(obj1, result)
            self.assertNotIn(obj2, result)
