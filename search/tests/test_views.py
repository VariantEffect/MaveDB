from django.test import TestCase, RequestFactory

from accounts.factories import UserFactory
from accounts.permissions import assign_user_as_instance_admin

from dataset.factories import ExperimentWithScoresetFactory

from ..views import search_view


class TestSearchView(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.path = '/search/'
        self.exp1 = ExperimentWithScoresetFactory()
        self.exp2 = ExperimentWithScoresetFactory()
        self.exp3 = ExperimentWithScoresetFactory()

    def test_private_entries_for_user_have_private_in_name(self):
        user = UserFactory()
        assign_user_as_instance_admin(user, self.exp1)
        request = self.factory.get(self.path)
        request.user = user
        response = search_view(request)
        contains = self.exp1.urn + ' [Private]'
        self.assertContains(response, contains)
        self.assertNotContains(response, self.exp2.urn)
        self.assertNotContains(response, self.exp3.urn)

    def test_can_search_by_user_and_dataset_fields(self):
        self.exp2.private = False
        self.exp2.save()
        self.exp1.title = 'Hello world'
        self.exp1.save()

        user = UserFactory()
        assign_user_as_instance_admin(user, self.exp1)
        scs = self.exp1.scoresets.first()
        scs.publish(propagate=True)
        scs.save(save_parents=True)
        self.assertFalse(self.exp1.private)

        assign_user_as_instance_admin(user, self.exp2)
        scs = self.exp2.scoresets.first()
        scs.publish(propagate=True)
        scs.save(save_parents=True)
        self.assertFalse(self.exp2.private)

        assign_user_as_instance_admin(user, self.exp1)
        request = self.factory.get(
            self.path + '/?username={}&title={}'.format(
                user.username, self.exp1.title))
        request.user = user

        response = search_view(request)
        self.assertContains(response, self.exp1.urn)
        self.assertNotContains(response, self.exp2.urn)
        self.assertNotContains(response, self.exp3.urn)

    def test_search_all_searches_all_fields_using_OR(self):
        self.exp1.private = False
        self.exp2.private = False
        self.exp2.title = 'Hello world'
        self.exp3.private = False
        self.exp1.save()
        self.exp2.save()
        self.exp3.save()

        user = UserFactory()
        assign_user_as_instance_admin(user, self.exp1)
        request = self.factory.get(
            self.path + '/?search={}&search={}'.format(
                user.username, self.exp2.title))

        response = search_view(request)
        self.assertContains(response, self.exp1.urn)
        self.assertContains(response, self.exp2.urn)
        self.assertNotContains(response, self.exp3.urn)

    def test_can_search_comma_sep_input(self):
        self.exp1.private = False
        self.exp1.title = "foo bar"
        self.exp2.private = False
        self.exp2.title = 'Hello world'
        self.exp3.private = False
        self.exp1.save()
        self.exp2.save()
        self.exp3.save()

        user = UserFactory()
        assign_user_as_instance_admin(user, self.exp1)
        request = self.factory.get(
            self.path + '/?search={}%2C{}'.format(
                self.exp1.title,
                self.exp2.title)
        )

        response = search_view(request)
        self.assertContains(response, self.exp1.urn)
        self.assertContains(response, self.exp2.urn)
        self.assertNotContains(response, self.exp3.urn)

    def test_double_quoted_comma_sep_not_split_input(self):
        self.exp1.private = False
        self.exp1.title = "foo bar"
        self.exp2.private = False
        self.exp2.title = '"Hello,world"'
        self.exp3.private = False
        self.exp1.save()
        self.exp2.save()
        self.exp3.save()

        user = UserFactory()
        assign_user_as_instance_admin(user, self.exp1)
        request = self.factory.get(
            self.path + '/?search={}%2C{}'.format(
                self.exp1.title,
                self.exp2.title)
        )

        response = search_view(request)
        self.assertContains(response, self.exp1.urn)
        self.assertContains(response, self.exp2.urn)
        self.assertNotContains(response, self.exp3.urn)
