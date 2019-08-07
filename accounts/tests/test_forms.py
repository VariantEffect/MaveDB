from django.test import TestCase, mock
from django.contrib.auth import get_user_model

from dataset.factories import (
    ExperimentFactory,
    ExperimentSetFactory,
    ScoreSetFactory,
)

from ..factories import UserFactory
from ..forms import SelectUsersForm
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
                "editors": [self.user1.pk],
            },
            instance=instance,
        )
        self.assertFalse(form.is_valid())

    def test_can_reassign_viewer_to_editor(self):
        instance = ExperimentFactory()
        instance.add_viewers(self.user2)
        form = SelectUsersForm(
            data={
                "administrators": [self.user1.pk],
                "editors": [self.user2.pk],
            },
            instance=instance,
        )
        self.assertFalse(form.errors)
        form.process_user_list()
        self.assertTrue(self.user2 in instance.editors)
        self.assertFalse(self.user2 in instance.viewers)

    def test_can_reassign_editor_to_admin(self):
        instance = ExperimentFactory()
        instance.add_editors(self.user2)
        form = SelectUsersForm(
            data={"administrators": [self.user1.pk, self.user2.pk]},
            instance=instance,
        )
        self.assertFalse(form.errors)
        form.process_user_list()
        self.assertTrue(self.user2 in instance.administrators)
        self.assertFalse(self.user2 in instance.editors)

    def test_can_reassign_admin_to_editor(self):
        instance = ExperimentFactory()
        instance.add_administrators(self.user2)
        form = SelectUsersForm(
            data={
                "administrators": [self.user1.pk],
                "editors": [self.user2.pk],
            },
            instance=instance,
        )
        self.assertFalse(form.errors)
        form.process_user_list()
        self.assertTrue(self.user2 in instance.editors)
        self.assertFalse(self.user2 in instance.administrators)

    def test_can_reassign_editor_to_viewer(self):
        instance = ExperimentFactory()
        instance.add_editors(self.user2)
        form = SelectUsersForm(
            data={
                "administrators": [self.user1.pk],
                "viewers": [self.user2.pk],
            },
            instance=instance,
        )
        self.assertFalse(form.errors)
        form.process_user_list()
        self.assertTrue(self.user2 in instance.viewers)
        self.assertFalse(self.user2 in instance.editors)

    def test_anon_not_in_queryset(self):
        instance = ExperimentFactory()
        form = SelectUsersForm(data={}, instance=instance)
        qs = form.fields["administrators"].queryset.all()
        self.assertFalse(any([user_is_anonymous(u) for u in qs]))

        qs = form.fields["editors"].queryset.all()
        self.assertFalse(any([user_is_anonymous(u) for u in qs]))

        qs = form.fields["viewers"].queryset.all()
        self.assertFalse(any([user_is_anonymous(u) for u in qs]))

    def test_superusers_not_in_query_list(self):
        instance = ExperimentFactory()
        form = SelectUsersForm(data={}, instance=instance)
        qs = form.fields["administrators"].queryset.all()
        self.assertFalse(all([u.is_superuser for u in qs]))

        qs = form.fields["editors"].queryset.all()
        self.assertFalse(all([u.is_superuser for u in qs]))

        qs = form.fields["viewers"].queryset.all()
        self.assertFalse(all([u.is_superuser for u in qs]))

    def test_can_set_initial_selected_users_from_instance(self):
        instance = ExperimentFactory()
        instance.add_administrators(self.user1)
        form = SelectUsersForm(data={}, instance=instance)
        self.assertIn(self.user1.pk, form.initial["administrators"])

        instance.add_editors(self.user1)
        form = SelectUsersForm(data={}, instance=instance)
        self.assertIn(self.user1.pk, form.initial["editors"])

        instance.add_viewers(self.user1)
        form = SelectUsersForm(data={}, instance=instance)
        self.assertIn(self.user1.pk, form.initial["viewers"])

    @mock.patch("accounts.models.Profile.notify_user_group_change")
    def test_reassigning_user_sends_email(self, patch):
        instance = ExperimentFactory()
        instance.add_editors(self.user1)
        form = SelectUsersForm(
            data={"administrators": [self.user1.pk]}, instance=instance
        )
        self.assertFalse(form.errors)
        form.process_user_list()
        patch.assert_called_with(
            **{
                "instance": instance,
                "action": "re-assigned",
                "group": GroupTypes.ADMIN,
            }
        )

    @mock.patch("accounts.models.Profile.notify_user_group_change")
    def test_adding_new_user_sends_email(self, patch):
        instance = ExperimentFactory()
        form = SelectUsersForm(
            data={"administrators": [self.user1.pk]}, instance=instance
        )
        self.assertFalse(form.errors)
        form.process_user_list()
        patch.assert_called_with(
            **{
                "instance": instance,
                "action": "added",
                "group": GroupTypes.ADMIN,
            }
        )

    @mock.patch("accounts.models.Profile.notify_user_group_change")
    def test_removing_user_sends_email(self, patch):
        instance = ExperimentFactory()
        instance.add_editors(self.user1)
        instance.add_administrators(self.user2)
        form = SelectUsersForm(
            data={"administrators": [self.user2.pk], "editors": []},
            instance=instance,
        )
        self.assertFalse(form.errors)
        form.process_user_list()
        patch.assert_called_with(
            **{
                "instance": instance,
                "action": "removed",
                "group": GroupTypes.EDITOR,
            }
        )

    @mock.patch("accounts.models.Profile.notify_user_group_change")
    def test_sends_mail_when_adding_user_as_viewer_to_parents(self, patch):
        instance = ScoreSetFactory()
        form = SelectUsersForm(
            data={"administrators": [self.user1.pk]}, instance=instance
        )
        self.assertFalse(form.errors)
        form.process_user_list()
        self.assertDictEqual(
            patch.call_args_list[0][1],
            {
                "instance": instance.parent,
                "action": "added",
                "group": GroupTypes.VIEWER,
            },
        )
        self.assertDictEqual(
            patch.call_args_list[1][1],
            {
                "instance": instance.parent.parent,
                "action": "added",
                "group": GroupTypes.VIEWER,
            },
        )

    def test_adds_user_as_viewer_to_parents_by_default(self):
        instance = ScoreSetFactory()
        form = SelectUsersForm(
            data={"administrators": [self.user1.pk]}, instance=instance
        )
        self.assertFalse(form.errors)
        form.process_user_list()
        self.assertIn(self.user1, instance.parent.viewers)
        self.assertIn(self.user1, instance.parent.parent.viewers)

    def test_does_not_change_parent_membership(self):
        instance = ScoreSetFactory()
        instance.parent.add_editors(self.user1)
        form = SelectUsersForm(
            data={"administrators": [self.user1.pk]}, instance=instance
        )
        self.assertFalse(form.errors)
        form.process_user_list()
        self.assertIn(self.user1, instance.parent.editors)
