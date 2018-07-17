from django.test import TestCase, RequestFactory

from core.utilities.tests import TestMessageMixin

from accounts.factories import UserFactory
from variant.factories import VariantFactory

import dataset
from dataset.factories import ScoreSetFactory

from ..utilities import delete, publish


class TestDelete(TestCase, TestMessageMixin):
    
    def setUp(self):
        self.user = UserFactory()
        self.factory = RequestFactory()
        
    def create_request(self, method='get', **kwargs):
        request = super().create_request(
            method=method, path='/profile/', **kwargs)
        request.user = self.user
        return request
        
    def test_false_object_does_not_exist(self):
        self.assertFalse(delete(None, self.create_request()))
        
    def test_false_user_does_not_have_manage_permissions(self):
        instance = ScoreSetFactory() # type: dataset.models.scoreset.ScoreSet
        
        instance.add_administrators(self.user)
        self.assertTrue(delete(instance.urn, self.create_request()))

        instance = ScoreSetFactory()
        instance.add_viewers(self.user)
        self.assertFalse(delete(instance.urn, self.create_request()))
        
        instance = ScoreSetFactory()
        instance.add_editors(self.user)
        self.assertFalse(delete(instance.urn, self.create_request()))
    
    def test_cannot_delete_experiment_if_has_children(self):
        instance = ScoreSetFactory()  # type: dataset.models.scoreset.ScoreSet
        experiment = instance.parent
        experiment.add_administrators(self.user)
        
        self.assertFalse(delete(experiment.urn, self.create_request()))
        dataset.utilities.delete_scoreset(instance)
        self.assertTrue(delete(experiment.urn, self.create_request()))

    def test_cannot_delete_experimentset_if_has_children(self):
        instance = ScoreSetFactory()  # type: dataset.models.scoreset.ScoreSet
        experiment = instance.parent
        experimentset = instance.parent.parent
        experimentset.add_administrators(self.user)
    
        self.assertFalse(delete(experimentset.urn, self.create_request()))
        dataset.utilities.delete_instance(experiment)
        self.assertTrue(delete(experimentset.urn, self.create_request()))
        
    def test_cannot_delete_when_being_processed(self):
        instance = ScoreSetFactory()  # type: dataset.models.scoreset.ScoreSet
        instance.processing_state = dataset.constants.processing
        instance.save()
        instance.add_administrators(self.user)
    
        self.assertFalse(delete(instance.urn, self.create_request()))
        instance.processing_state = dataset.constants.success
        instance.save()
        self.assertTrue(delete(instance.urn, self.create_request()))
        
    def test_cannot_delete_public_instance(self):
        instance = ScoreSetFactory()  # type: dataset.models.scoreset.ScoreSet
        instance.publish()
        instance.save()
        instance.add_administrators(self.user)
        self.assertFalse(delete(instance.urn, self.create_request()))


class TestPublish(TestCase, TestMessageMixin):
    def setUp(self):
        self.user = UserFactory()
        self.factory = RequestFactory()
    
    def create_request(self, method='get', **kwargs):
        request = super().create_request(
            method=method, path='/profile/', **kwargs)
        request.user = self.user
        return request
    
    @staticmethod
    def create_scoreset():
        """
        Create a minimal scoreset with variants.
        
        Returns
        -------
        py:class:`dataset.models.scoreset.ScoreSet`
            A `ScoreSet` instance
        """
        scoreset = ScoreSetFactory()
        for i in range(3):
            VariantFactory(scoreset=scoreset)
        return scoreset
        
    def test_false_object_does_not_exist(self):
        self.assertFalse(publish(None, self.create_request()))

    def test_false_user_does_not_have_manage_permissions(self):
        scoreset = self.create_scoreset()
        scoreset.add_administrators(self.user)
        self.assertTrue(publish(scoreset.urn, self.create_request()))

        scoreset = self.create_scoreset()
        scoreset.add_editors(self.user)
        self.assertFalse(publish(scoreset.urn, self.create_request()))
        
        scoreset = self.create_scoreset()
        scoreset.add_viewers(self.user)
        self.assertFalse(publish(scoreset.urn, self.create_request()))
        
    def test_false_not_a_scoreset(self):
        scoreset = self.create_scoreset()
        scoreset.parent.add_administrators(self.user)
        self.assertFalse(
            publish(scoreset.parent.urn, self.create_request()))
    
    def test_false_publish_when_being_processed(self):
        scoreset = self.create_scoreset()
        scoreset.add_administrators(self.user)
        
        scoreset.processing_state = dataset.constants.processing
        scoreset.save()
        self.assertFalse(publish(scoreset.urn, self.create_request()))
        
        scoreset.processing_state = dataset.constants.success
        scoreset.save()
        self.assertTrue(publish(scoreset.urn, self.create_request()))
    
    def test_false_publish_in_fail_state(self):
        scoreset = self.create_scoreset()
        scoreset.add_administrators(self.user)
    
        scoreset.processing_state = dataset.constants.failed
        scoreset.save()
        self.assertFalse(publish(scoreset.urn, self.create_request()))
    
        scoreset.processing_state = dataset.constants.success
        scoreset.save()
        self.assertTrue(publish(scoreset.urn, self.create_request()))
    
    def test_false_publish_not_variants(self):
        scoreset = self.create_scoreset()
        scoreset.add_administrators(self.user)
        self.assertTrue(publish(scoreset.urn, self.create_request()))
    
        scoreset = self.create_scoreset()
        scoreset.add_administrators(self.user)
        scoreset.variants.all().delete()
        self.assertFalse(publish(scoreset.urn, self.create_request()))
    
    def test_false_already_public(self):
        scoreset = self.create_scoreset()
        scoreset.add_administrators(self.user)
        scoreset.publish()
        self.assertFalse(publish(scoreset.urn, self.create_request()))
    