from django.test import TestCase
from django.contrib.auth import get_user_model

from dataset.factories import ExperimentFactory

from ..forms import SelectUsersForm
from ..permissions import (
    GroupTypes,
    user_is_anonymous,
    user_is_contributor_for_instance,
    assign_user_as_instance_admin,
    assign_user_as_instance_viewer
)

User = get_user_model()


class TestSelectUsersForm(TestCase):

    def setUp(self):
        self.alice = User.objects.create(username="alice")
        self.bob = User.objects.create(username="bob")

    def test_can_admin_form_invalid_blank_data(self):
        instance = ExperimentFactory()
        form = SelectUsersForm(
			user=self.alice,
            data={},
            group=GroupTypes.ADMIN,
            instance=instance,
            required=False
        )
        self.assertFalse(form.is_valid())

    def test_can_non_admin_form_valid_blank_data(self):
        instance = ExperimentFactory()
        form = SelectUsersForm(
			user=self.alice,
            data={},
            group=GroupTypes.VIEWER,
            instance=instance,
            required=False
        )
        self.assertTrue(form.is_valid())

        form = SelectUsersForm(
			user=self.alice,
            data={},
            group=GroupTypes.EDITOR,
            instance=instance,
            required=False
        )
        self.assertTrue(form.is_valid())

    def test_error_not_supported_group_type(self):
        instance = ExperimentFactory()
        with self.assertRaises(ValueError):
            SelectUsersForm(
			user=self.alice,
                data={},
                group="not a group type",
                instance=instance,
                required=False
            )

    def test_validation_error_cannot_assign_empty_admin_list(self):
        instance = ExperimentFactory()
        form = SelectUsersForm(
			user=self.alice,
            data={"users": []},
            group=GroupTypes.ADMIN,
            instance=instance,
            required=False
        )
        self.assertFalse(form.is_valid())

    def test_validation_error_cannot_reassign_only_admin(self):
        instance = ExperimentFactory()
        assign_user_as_instance_admin(self.alice, instance)
        form = SelectUsersForm(
			user=self.alice,
            data={"users": [self.alice.pk]},
            group=GroupTypes.EDITOR,
            instance=instance,
            required=False
        )
        self.assertFalse(form.is_valid())

    def test_can_set_required_field_param_inside_init(self):
        instance = ExperimentFactory()
        form = SelectUsersForm(
			user=self.alice,
            data={},
            group=GroupTypes.VIEWER,
            instance=instance,
            required=True
        )
        self.assertFalse(form.is_valid())

    def test_can_successfully_reasign_members(self):
        instance = ExperimentFactory()
        assign_user_as_instance_viewer(self.alice, instance)
        form = SelectUsersForm(
			user=self.alice,
            data={"users": [self.alice.pk]},
            group=GroupTypes.EDITOR,
            instance=instance,
            required=False
        )
        form.process_user_list()
        self.assertTrue(user_is_contributor_for_instance(self.alice, instance))

    def test_anon_not_in_queryset(self):
        instance = ExperimentFactory()
        form = SelectUsersForm(
			user=self.alice,
            data={},
            group=GroupTypes.VIEWER,
            instance=instance,
            required=True
        )
        qs = form.fields["users"].queryset.all()
        self.assertFalse(
            any([user_is_anonymous(u) for u in qs])
        )

    def test_superusers_not_in_query_list(self):
        instance = ExperimentFactory()
        form = SelectUsersForm(
			user=self.alice,
            data={},
            group=GroupTypes.VIEWER,
            instance=instance,
            required=True
        )
        qs = form.fields["users"].queryset.all()
        self.assertTrue(all([not u.is_superuser for u in qs]))

    def test_can_set_initial_selected_users_from_instance(self):
        instance = ExperimentFactory()
        assign_user_as_instance_admin(self.alice, instance)
        form = SelectUsersForm(
			user=self.alice,
            data={},
            group=GroupTypes.ADMIN,
            instance=instance,
            required=False
        )
        self.assertTrue(self.alice.pk in form.initial["users"])

    def test_validation_error_IGNORED_superuser_reassign_only_admin(self):
            instance = ExperimentFactory()
            assign_user_as_instance_admin(self.alice, instance)
            self.alice.is_superuser = True
            self.alice.save()
            form = SelectUsersForm(
                user=self.alice,
                data={"users": [self.alice.pk]},
                group=GroupTypes.EDITOR,
                instance=instance,
                required=False
            )
            self.assertTrue(form.is_valid())

    def test_validation_error_IGNORED_superuser_assign_empty_admin_list(self):
        instance = ExperimentFactory()
        self.alice.is_superuser = True
        self.alice.save()
        form = SelectUsersForm(
            user=self.alice,
            data={"users": []},
            group=GroupTypes.ADMIN,
            instance=instance,
            required=False
        )
        self.assertTrue(form.is_valid())