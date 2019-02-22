from django.test import TestCase
from django.contrib.auth import get_user_model

from .. import filters
from ..factories import UserFactory, AnonymousUserFactory

User = get_user_model()


class TestUserFilter(TestCase):
    def setUp(self):
        self.user1 = UserFactory(first_name='Alice', last_name='Mare')
        self.user2 = UserFactory(first_name='David', last_name='Davidson')
        self.queryset = User.objects.all()

    def test_empty_search_all_results(self):
        f = filters.UserFilter(queryset=self.queryset, data={})
        self.assertEqual(f.qs.count(), 2)

    def test_filters_out_anon(self):
        AnonymousUserFactory()
        f = filters.UserFilter(queryset=self.queryset, data={})
        self.assertEqual(f.qs.count(), 2)
        self.assertIn(self.user1, f.qs)
        self.assertIn(self.user2, f.qs)

    def test_filters_out_superusers(self):
        self.user2.is_superuser = True
        self.user2.save()
        f = filters.UserFilter(queryset=self.queryset, data={})
        self.assertEqual(f.qs.count(), 1)
        self.assertIn(self.user1, f.qs)

    def test_search_by_first_name(self):
        f = filters.UserFilter(
            queryset=self.queryset,
            data={filters.UserFilter.FIRST_NAME: self.user1.first_name}
        )
        self.assertEqual(f.qs.count(), 1)
        self.assertIn(self.user1, f.qs)

    def test_search_by_last_name(self):
        f = filters.UserFilter(
            queryset=self.queryset,
            data={filters.UserFilter.LAST_NAME: self.user1.last_name}
        )
        self.assertEqual(f.qs.count(), 1)
        self.assertIn(self.user1, f.qs)

    def test_search_by_username(self):
        f = filters.UserFilter(
            queryset=self.queryset,
            data={filters.UserFilter.USERNAME: self.user1.username}
        )
        self.assertEqual(f.qs.count(), 1)
        self.assertIn(self.user1, f.qs)

    def test_search_by_display_name(self):
        f = filters.UserFilter(
            queryset=self.queryset,
            data={filters.UserFilter.DISPLAY_NAME:
                      self.user1.profile.get_display_name()}
        )
        self.assertEqual(f.qs.count(), 1)
        self.assertIn(self.user1, f.qs)

    def test_search_by_display_name_csv(self):
        f = filters.UserFilter(
            queryset=self.queryset,
            data={
                filters.UserFilter.DISPLAY_NAME: '{},{}'.format(
                    self.user1.profile.get_display_name(),
                    self.user2.profile.get_display_name()
                )
            }
        )
        self.assertEqual(f.qs.count(), 2)
        self.assertIn(self.user1, f.qs)

    def test_searching_multiple_fields_joins_results_by_AND(self):
        # No results since the two querysets are disjoint
        f = filters.UserFilter(
            queryset=self.queryset,
            data={
                filters.UserFilter.LAST_NAME: self.user1.last_name,
                filters.UserFilter.FIRST_NAME: self.user2.first_name,
            }
        )
        self.assertEqual(f.qs.count(), 0)

        # Should return first instance only
        f = filters.UserFilter(
            queryset=self.queryset,
            data={
                filters.UserFilter.LAST_NAME: self.user1.last_name,
                filters.UserFilter.FIRST_NAME: self.user1.first_name,
            }
        )
        self.assertEqual(f.qs.count(), 1)
        self.assertIn(self.user1, f.qs.all())
