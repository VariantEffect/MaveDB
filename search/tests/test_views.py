from django.test import TestCase, RequestFactory

from accounts.factories import UserFactory

from dataset.factories import ExperimentWithScoresetFactory
from dataset import utilities

from ..views import search_view


class TestSearchView(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.path = '/search/'
        self.exp1 = ExperimentWithScoresetFactory()
        self.exp2 = ExperimentWithScoresetFactory()
        self.exp3 = ExperimentWithScoresetFactory()
        self.scs1 = self.exp1.scoresets.first()
        self.scs2 = self.exp2.scoresets.first()
        self.scs3 = self.exp3.scoresets.first()

        self.scs1 = utilities.publish_dataset(self.scs1)
        self.scs2 = utilities.publish_dataset(self.scs2)
        self.scs3 = utilities.publish_dataset(self.scs3)

        self.exp1.refresh_from_db()
        self.exp2.refresh_from_db()
        self.exp3.refresh_from_db()

    def test_private_entries_for_user_have_private_in_name(self):
        user = UserFactory()
        self.exp1.private = True
        self.exp1.add_administrators(user)
        self.scs1.add_administrators(user)
        self.scs1.private = True

        self.exp1.save()
        self.scs1.save()

        request = self.factory.get(self.path)
        request.user = user
        response = search_view(request)

        self.assertContains(response, self.exp1.urn + ' [Private]')
        self.assertContains(response, self.scs1.urn + ' [Private]')

    def test_search_empty_returns_all_public_and_private_viewable(self):
        request = self.factory.get(self.path + '/')
        response = search_view(request)
        self.assertContains(response, self.exp1.urn + '/')
        self.assertContains(response, self.exp2.urn + '/')
        self.assertContains(response, self.exp3.urn + '/')

        self.assertContains(response, self.scs1.urn + '/')
        self.assertContains(response, self.scs2.urn + '/')
        self.assertContains(response, self.scs3.urn + '/')
        
    def test_basic_search_delegates_to_basic_form(self):
        request = self.factory.get(self.path + '/?search={}'.format(
            self.exp1.urn))
        response = search_view(request)
        self.assertContains(response, self.exp1.urn + '/')
        self.assertNotContains(response, self.exp2.urn + '/')
        self.assertNotContains(response, self.exp3.urn + '/')

        self.assertNotContains(response, self.scs1.urn + '/')
        self.assertNotContains(response, self.scs2.urn + '/')
        self.assertNotContains(response, self.scs3.urn + '/')
        
    def test_adv_search_delegates_to_adv_form(self):
        request = self.factory.get(self.path + '/?title={}'.format(
            self.exp1.title))
        response = search_view(request)
        self.assertContains(response, self.exp1.urn + '/')
        self.assertNotContains(response, self.exp2.urn + '/')
        self.assertNotContains(response, self.exp3.urn + '/')

        self.assertNotContains(response, self.scs1.urn + '/')
        self.assertNotContains(response, self.scs2.urn + '/')
        self.assertNotContains(response, self.scs3.urn + '/')
