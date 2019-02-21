from django.test import TestCase, RequestFactory, mock
from django.contrib.auth import get_user_model

from accounts.factories import UserFactory

from dataset import factories
from dataset import utilities

from .. import views


User = get_user_model()


class TestUtilities(TestCase):
    def test_group_groups_scoresets_under_parent(self):
        exp = factories.ExperimentFactory()
        scs1 = factories.ScoreSetFactory(experiment=exp)
        scs2 = factories.ScoreSetFactory(experiment=exp)
        user = UserFactory()
        results = views.group_children([exp], [scs1, scs2], user=user)
        expected = {exp: list(
            sorted({scs1, scs2}, key=lambda i: i.urn))
        }
        self.assertDictEqual(results, expected)

    def test_group_adds_parents_to_keys_if_missing(self):
        scs = factories.ScoreSetFactory()
        user = UserFactory()
        results = views.group_children([], [scs], user=user)
        expected = {scs.parent: [scs]}
        self.assertDictEqual(results, expected)
        
    def test_replaces_child_with_most_recent_for_user(self):
        scs1 = factories.ScoreSetFactory()
        scs2 = factories.ScoreSetFactory(
            replaces=scs1, experiment=scs1.experiment
        )
        user = UserFactory()
        scs2.add_viewers(user)
        
        results = views.group_children([], [scs1], user=user)
        expected = {scs2.parent: [scs2, ]}
        self.assertDictEqual(results, expected)

    def test_replaces_child_with_most_recent(self):
        scs1 = factories.ScoreSetFactory(private=False)
        _ = factories.ScoreSetFactory(
            replaces=scs1, experiment=scs1.experiment
        )
        user = UserFactory()
        results = views.group_children([], [scs1], user=user)
        expected = {scs1.parent: [scs1, ]}
        self.assertDictEqual(results, expected)


class TestToJson(TestCase):
    def setUp(self):
        self.exp = factories.ExperimentWithScoresetFactory()
        self.user = UserFactory()

    @mock.patch("search.views.display_targets", return_value=[])
    def test_calls_display_targets(self, patch):
        grouped = {self.exp: self.exp.children}
        views.to_json(grouped, user=self.user)
        patch.assert_called()

    @mock.patch("search.views.format_urn_name_for_user", return_value="")
    def test_calls_format_urn_name_for_user_with_user(self, patch):
        grouped = {self.exp: self.exp.children}
        views.to_json(grouped, user=self.user)
        patch.assert_called_with(*(self.exp, self.user,))

    def test_contributor_names_contains_contributors_only(self):
        grouped = {self.exp: self.exp.children}

        user1 = UserFactory()
        user2 = UserFactory()
        self.exp.add_administrators(user1)
        self.exp.children.first().add_administrators(user1)

        result = views.to_json(grouped, user=self.user)
        self.assertIn(user1.username, result[0]['contributors'])
        self.assertNotIn(user2.username, result[0]['contributors'])

        self.assertIn(user1.username, result[0]['children'][0]['contributors'])
        self.assertNotIn(user2.username, result[0]['children'][0]['contributors'])


class TestSearchView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.path = '/search/'
        self.exp1 = factories.ExperimentWithScoresetFactory()
        self.exp2 = factories.ExperimentWithScoresetFactory()
        self.exp3 = factories.ExperimentWithScoresetFactory()
        self.scs1 = self.exp1.scoresets.first()
        self.scs2 = self.exp2.scoresets.first()
        self.scs3 = self.exp3.scoresets.first()

        self.scs1 = utilities.publish_dataset(self.scs1)
        self.scs2 = utilities.publish_dataset(self.scs2)
        self.scs3 = utilities.publish_dataset(self.scs3)

        self.exp1.refresh_from_db()
        self.exp2.refresh_from_db()
        self.exp3.refresh_from_db()

    @mock.patch("search.views.filter_visible", return_value=[])
    def test_calls_filter_visible(self, patch):
        request = self.factory.get(
            self.path, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = UserFactory()
        views.search_view(request)
        patch.assert_called()

    @mock.patch("search.views.group_children", return_value={})
    def test_calls_group_children(self, patch):
        request = self.factory.get(
            self.path, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = UserFactory()
        views.search_view(request)
        patch.assert_called()

    @mock.patch("search.views.to_json", return_value={})
    def test_calls_to_json(self, patch):
        request = self.factory.get(
            self.path, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = UserFactory()
        views.search_view(request)
        patch.assert_called()

    def test_private_entries_for_user_have_private_in_name(self):
        user = UserFactory()
        self.exp1.private = True
        self.exp1.add_administrators(user)

        self.scs1.add_administrators(user)
        self.scs1.private = True

        self.exp1.save()
        self.scs1.save()

        request = self.factory.get(
            self.path, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = user

        response = views.search_view(request)
        self.assertContains(response, '{} [Private]'.format(self.exp1.urn))
        self.assertContains(response, '{} [Private]'.format(self.scs1.urn))

    def test_search_empty_returns_all_public(self):
        request = self.factory.get(
            self.path, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = UserFactory()
        response = views.search_view(request)

        self.assertContains(response, self.exp1.urn)
        self.assertContains(response, self.exp2.urn)
        self.assertContains(response, self.exp3.urn)

        self.assertContains(response, self.scs1.urn)
        self.assertContains(response, self.scs2.urn)
        self.assertContains(response, self.scs3.urn)

    def test_search_shows_tmp_parent_if_user_not_contributor(self):
        request = self.factory.get(
            self.path, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        user = UserFactory()
        request.user = user
        response = views.search_view(request)

        self.exp1.private = True

        self.scs1.add_administrators(user)
        self.scs1.private = True

        self.assertContains(response, self.exp1.urn)
        self.assertContains(response, self.scs1.urn)

    def test_basic_search_delegates_to_basic_form(self):
        request = self.factory.get(self.path + '/?search={}'.format(
            self.exp1.urn), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        request.user = UserFactory()
        response = views.search_view(request)
        self.assertContains(response, self.exp1.urn)
        self.assertNotContains(response, self.exp2.urn)
        self.assertNotContains(response, self.exp3.urn)
        self.assertNotContains(response, self.scs1.urn)
        self.assertNotContains(response, self.scs2.urn)
        self.assertNotContains(response, self.scs3.urn)

    def test_adv_search_delegates_to_adv_form(self):
        request = self.factory.get(self.path + '/?title={}'.format(
            self.exp1.title), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = UserFactory()
        response = views.search_view(request)
        self.assertContains(response, self.exp1.urn)
        self.assertNotContains(response, self.exp2.urn)
        self.assertNotContains(response, self.exp3.urn)
        self.assertNotContains(response, self.scs1.urn)
        self.assertNotContains(response, self.scs2.urn)
        self.assertNotContains(response, self.scs3.urn)
