from django.test import TestCase, mock
from django.core import mail
from django.contrib.auth import get_user_model

from dataset.factories import ExperimentFactory

from ..factories import UserFactory
from ..forms import SelectUsersForm, UserSearchForm
from ..mixins import UserFilterMixin
from ..permissions import GroupTypes, user_is_anonymous

User = get_user_model()


class TestSelectUsersForm(TestCase):
    def setUp(self):
        self.user1 = UserFactory()
        self.user2 = UserFactory()

    def test_form_invalid_cannot_assign_empty_admin_list(self):
        instance = ExperimentFactory()
        form = SelectUsersForm(data={"administrators": []}, instance=instance)
        self.assertFalse(form.is_valid())

    def test_form_invalid_user_assigned_to_multiple_groups(self):
        instance = ExperimentFactory()
        instance.add_administrators(self.user1)
        form = SelectUsersForm(
            data={
                "administrators": [self.user1.pk],
                "editors": [self.user1.pk]
            },
            instance=instance,
        )
        self.assertFalse(form.is_valid())
        print(form.errors)

    def test_can_reassign_viewer_to_editor(self):
        instance = ExperimentFactory()
        instance.add_viewers(self.user2)
        form = SelectUsersForm(
            data={
                "administrators": [self.user1.pk],
                "editors": [self.user2.pk]
            },
            instance=instance,
        )
        self.assertFalse(form.errors)
        form.process_user_list()
        self.assertTrue(self.user2 in instance.editors())
        self.assertFalse(self.user2 in instance.viewers())
        
    def test_can_reassign_editor_to_admin(self):
        instance = ExperimentFactory()
        instance.add_editors(self.user2)
        form = SelectUsersForm(
            data={
                "administrators": [self.user1.pk, self.user2.pk],
            },
            instance=instance,
        )
        self.assertFalse(form.errors)
        form.process_user_list()
        self.assertTrue(self.user2 in instance.administrators())
        self.assertFalse(self.user2 in instance.editors())

    def test_can_reassign_admin_to_editor(self):
        instance = ExperimentFactory()
        instance.add_administrators(self.user2)
        form = SelectUsersForm(
            data={
                "administrators": [self.user1.pk],
                "editors": [self.user2.pk]
            },
            instance=instance,
        )
        self.assertFalse(form.errors)
        form.process_user_list()
        self.assertTrue(self.user2 in instance.editors())
        self.assertFalse(self.user2 in instance.administrators())
        
    def test_can_reassign_editor_to_viewer(self):
        instance = ExperimentFactory()
        instance.add_editors(self.user2)
        form = SelectUsersForm(
            data={
                "administrators": [self.user1.pk],
                "viewers": [self.user2.pk]
            },
            instance=instance,
        )
        self.assertFalse(form.errors)
        form.process_user_list()
        self.assertTrue(self.user2 in instance.viewers())
        self.assertFalse(self.user2 in instance.editors())
    
    def test_anon_not_in_queryset(self):
        instance = ExperimentFactory()
        form = SelectUsersForm(data={}, instance=instance,)
        qs = form.fields["administrators"].queryset.all()
        self.assertFalse(any([user_is_anonymous(u) for u in qs]))
        
        qs = form.fields["editors"].queryset.all()
        self.assertFalse(any([user_is_anonymous(u) for u in qs]))
        
        qs = form.fields["viewers"].queryset.all()
        self.assertFalse(any([user_is_anonymous(u) for u in qs]))

    def test_superusers_not_in_query_list(self):
        instance = ExperimentFactory()
        form = SelectUsersForm(data={}, instance=instance, )
        qs = form.fields["administrators"].queryset.all()
        self.assertFalse(all([u.is_superuser for u in qs]))
    
        qs = form.fields["editors"].queryset.all()
        self.assertFalse(all([u.is_superuser for u in qs]))
    
        qs = form.fields["viewers"].queryset.all()
        self.assertFalse(all([u.is_superuser for u in qs]))

    def test_can_set_initial_selected_users_from_instance(self):
        instance = ExperimentFactory()
        instance.add_administrators(self.user1)
        form = SelectUsersForm(data={}, instance=instance,)
        self.assertIn(self.user1.pk, form.initial["administrators"])
        
        instance.add_editors(self.user1)
        form = SelectUsersForm(data={}, instance=instance,)
        self.assertIn(self.user1.pk, form.initial["editors"])
        
        instance.add_viewers(self.user1)
        form = SelectUsersForm(data={}, instance=instance,)
        self.assertIn(self.user1.pk, form.initial["viewers"])
    
    @mock.patch("accounts.models.Profile.notify_user_group_change")
    def test_reassigning_user_sends_email(self, patch):
        instance = ExperimentFactory()
        instance.add_editors(self.user1)
        form = SelectUsersForm(
            data={"administrators": [self.user1.pk]},
            instance=instance,
        )
        self.assertFalse(form.errors)
        form.process_user_list()
        patch.assert_called_with(**{
            'instance': instance,
            'action': 're-assigned',
            'group': GroupTypes.ADMIN,
        })

    @mock.patch("accounts.models.Profile.notify_user_group_change")
    def test_adding_new_user_sends_email(self, patch):
        instance = ExperimentFactory()
        form = SelectUsersForm(
            data={"administrators": [self.user1.pk]},
            instance=instance,
        )
        self.assertFalse(form.errors)
        form.process_user_list()
        patch.assert_called_with(**{
            'instance': instance,
            'action': 'added',
            'group': GroupTypes.ADMIN,
        })
        
    @mock.patch("accounts.models.Profile.notify_user_group_change")
    def test_removing_user_sends_email(self, patch):
        instance = ExperimentFactory()
        instance.add_editors(self.user1)
        form = SelectUsersForm(
            data={
                "administrators": [self.user2.pk],
                "editors": [],
            },
            instance=instance,
        )
        self.assertFalse(form.errors)
        form.process_user_list()
        patch.assert_called_with(**{
            'instance': instance,
            'action': 'removed',
            'group': GroupTypes.EDITOR,
        })


class TestUserSearchForm(TestCase):

    def test_can_search_by_first_name(self):
        u1 = UserFactory(first_name='Bob')
        u2 = UserFactory(first_name='Alice')

        dict_ = {UserFilterMixin.FIRST_NAME: 'bob'}
        form = UserSearchForm(data=dict_)
        self.assertTrue(form.is_valid())
        q = form.make_filters(join=True)

        result = User.objects.filter(q).distinct()
        self.assertEqual(result.count(), 1)
        self.assertIn(u1, result)
        self.assertNotIn(u2, result)

    def test_can_search_by_last_name(self):
        u1 = UserFactory(last_name='McBob')
        u2 = UserFactory(last_name='McAlice')

        dict_ = {UserFilterMixin.LAST_NAME: 'McBob'}
        form = UserSearchForm(data=dict_)
        self.assertTrue(form.is_valid())
        q = form.make_filters(join=True)

        result = User.objects.filter(q).distinct()
        self.assertEqual(result.count(), 1)
        self.assertIn(u1, result)
        self.assertNotIn(u2, result)

    def test_can_search_by_username(self):
        u1 = UserFactory(username='uBob')
        u2 = UserFactory(username='uAlice')

        dict_ = {UserFilterMixin.USERNAME: 'ubob'}
        form = UserSearchForm(data=dict_)
        self.assertTrue(form.is_valid())
        q = form.make_filters(join=True)

        result = User.objects.filter(q).distinct()
        self.assertEqual(result.count(), 1)
        self.assertIn(u1, result)
        self.assertNotIn(u2, result)

    def test_can_search_multiple_fields(self):
        u1 = UserFactory(username='000-000-X')
        u2 = UserFactory(first_name='Alice')
        u3 = UserFactory(first_name='Bob')

        dict_ = {
            UserFilterMixin.FIRST_NAME: 'alice',
            UserFilterMixin.USERNAME: '000-000-X'
        }
        form = UserSearchForm(data=dict_)
        self.assertTrue(form.is_valid())
        q = form.make_filters(join=True)

        result = User.objects.filter(q).distinct()
        self.assertEqual(result.count(), 2)
        self.assertIn(u1, result)
        self.assertIn(u2, result)
        self.assertNotIn(u3, result)

    def test_search_is_case_insensitive(self):
        UserFactory(username='USER')
        UserFactory(first_name='User')
        UserFactory(first_name='UsEr')

        dict_ = {
            UserFilterMixin.FIRST_NAME: 'user',
            UserFilterMixin.LAST_NAME: 'user',
            UserFilterMixin.USERNAME: 'user'
        }
        form = UserSearchForm(data=dict_)
        self.assertTrue(form.is_valid())
        q = form.make_filters(join=True)

        result = User.objects.filter(q).distinct()
        self.assertEqual(result.count(), 3)
