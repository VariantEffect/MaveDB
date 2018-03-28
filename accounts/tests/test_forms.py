from django.http import QueryDict
from django.test import TestCase
from django.contrib.auth import get_user_model

from dataset.models import Experiment

from ..forms import SelectUsersForm
from ..permissions import (
    GroupTypes,
    user_is_anonymous,
    user_is_admin_for_instance,
    user_is_contributor_for_instance,
    user_is_viewer_for_instance,
    assign_user_as_instance_admin,
    assign_user_as_instance_contributor,
    assign_user_as_instance_viewer
)

User = get_user_model()


class TestSelectUsersForm(TestCase):

    def setUp(self):
        self.alice = User.objects.create(username="alice")
        self.bob = User.objects.create(username="bob")

    def test_can_admin_form_invalid_blank_data(self):
        instance = Experiment.objects.create(target="test", wt_sequence="atcg")
        form = SelectUsersForm(
            data={},
            group=GroupTypes.ADMIN,
            instance=instance,
            required=False
        )
        self.assertFalse(form.is_valid())

    def test_can_non_admin_form_valid_blank_data(self):
        instance = Experiment.objects.create(target="test", wt_sequence="atcg")
        form = SelectUsersForm(
            data={},
            group=GroupTypes.VIEWER,
            instance=instance,
            required=False
        )
        self.assertTrue(form.is_valid())

        form = SelectUsersForm(
            data={},
            group=GroupTypes.CONTRIBUTOR,
            instance=instance,
            required=False
        )
        self.assertTrue(form.is_valid())

    def test_error_not_supported_group_type(self):
        instance = Experiment.objects.create(target="test", wt_sequence="atcg")
        with self.assertRaises(ValueError):
            SelectUsersForm(
                data={},
                group="not a group type",
                instance=instance,
                required=False
            )

    def test_validation_error_cannot_assign_empty_admin_list(self):
        instance = Experiment.objects.create(target="test", wt_sequence="atcg")
        form = SelectUsersForm(
            data={"users": []},
            group=GroupTypes.ADMIN,
            instance=instance,
            required=False
        )
        self.assertFalse(form.is_valid())

    def test_validation_error_cannot_reassign_only_admin(self):
        instance = Experiment.objects.create(target="test", wt_sequence="atcg")
        assign_user_as_instance_admin(self.alice, instance)
        form = SelectUsersForm(
            data={"users": [self.alice.pk]},
            group=GroupTypes.CONTRIBUTOR,
            instance=instance,
            required=False
        )
        self.assertFalse(form.is_valid())

    def test_can_set_required_field_param_inside_init(self):
        instance = Experiment.objects.create(target="test", wt_sequence="atcg")
        form = SelectUsersForm(
            data={},
            group=GroupTypes.VIEWER,
            instance=instance,
            required=True
        )
        self.assertFalse(form.is_valid())

    def test_can_successfully_reasign_members(self):
        instance = Experiment.objects.create(target="test", wt_sequence="atcg")
        assign_user_as_instance_viewer(self.alice, instance)
        form = SelectUsersForm(
            data={"users": [self.alice.pk]},
            group=GroupTypes.CONTRIBUTOR,
            instance=instance,
            required=False
        )
        form.process_user_list()
        self.assertTrue(user_is_contributor_for_instance(self.alice, instance))

    def test_anon_not_in_queryset(self):
        instance = Experiment.objects.create(target="test", wt_sequence="atcg")
        form = SelectUsersForm(
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
        instance = Experiment.objects.create(target="test", wt_sequence="atcg")
        form = SelectUsersForm(
            data={},
            group=GroupTypes.VIEWER,
            instance=instance,
            required=True
        )
        qs = form.fields["users"].queryset.all()
        self.assertTrue(all([not u.is_superuser for u in qs]))

    def test_can_set_initial_selected_users_from_instance(self):
        instance = Experiment.objects.create(target="test", wt_sequence="atcg")
        assign_user_as_instance_admin(self.alice, instance)
        form = SelectUsersForm(
            data={},
            group=GroupTypes.ADMIN,
            instance=instance,
            required=False
        )
        self.assertTrue(self.alice.pk in form.initial["users"])
