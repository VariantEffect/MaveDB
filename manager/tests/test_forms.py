from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase, RequestFactory

from .. import forms
from .. import models
from accounts.models import User
from dataset import constants
from main.models import News
from urn.models import generate_tmp_urn


class TestAddPmidForm(TestCase):
    def test_field_validation(self):
        urn_field_name = "urn"
        pmid_field_name = "pmid"

        # Fields are empty
        urn = ""
        pmid = ""
        form = forms.AddPmidForm(
            data={urn_field_name: urn, pmid_field_name: pmid}
        )
        self.assertTrue(
            "This field is required." in form.errors[urn_field_name]
        )
        self.assertTrue(
            "This field is required." in form.errors[pmid_field_name]
        )

        # Fields are invalid
        urn = "invalid_urn"
        pmid = "invalid_pmid"
        form = forms.AddPmidForm(
            data={urn_field_name: urn, pmid_field_name: pmid}
        )
        self.assertTrue(
            f"{urn} is not a valid urn." in form.errors[urn_field_name]
        )
        self.assertTrue(
            f"{pmid} is not a valid PubMed ID." in form.errors[pmid_field_name]
        )

        # Fields are valid
        urn = generate_tmp_urn()
        pmid = "123456789"
        form = forms.AddPmidForm(
            data={urn_field_name: urn, pmid_field_name: pmid}
        )
        self.assertTrue(form.is_valid())


class TestAddUserForm(TestCase):
    def test_field_validation(self):
        urn_field_name = "urn"
        user_id_field_name = "user_id"
        role_field_name = "role"

        # Fields are empty
        urn = ""
        user_id = ""
        role = ""
        form = forms.AddUserForm(
            data={
                urn_field_name: urn,
                user_id_field_name: user_id,
                role_field_name: role,
            }
        )
        self.assertTrue(
            "This field is required." in form.errors[urn_field_name]
        )
        self.assertTrue(
            "This field is required." in form.errors[user_id_field_name]
        )
        self.assertTrue(
            "This field is required." in form.errors[role_field_name]
        )

        # Fields are invalid
        max_length = 100
        extra_length = max_length + 1
        urn = "invalid_urn"
        user_id = "fake_user_id"
        role = "invalid_role"
        form = forms.AddUserForm(
            data={
                urn_field_name: urn,
                user_id_field_name: user_id,
                role_field_name: role,
            }
        )
        self.assertTrue(
            f"{urn} is not a valid urn." in form.errors[urn_field_name]
        )
        self.assertTrue(
            f"User with id {user_id} does not exist."
            in form.errors[user_id_field_name]
        )
        self.assertTrue(
            f"Invalid user role {role}." in form.errors[role_field_name]
        )

        # Fields are valid
        valid_roles = (
            constants.administrator,
            constants.editor,
            constants.viewer,
        )
        urn = generate_tmp_urn()
        user_id = "real_user_id"
        user = User(username=user_id)
        user.set_password("password")
        user.save()
        for valid_role in valid_roles:
            role = valid_role
            form = forms.AddUserForm(
                data={
                    urn_field_name: urn,
                    user_id_field_name: user_id,
                    role_field_name: role,
                }
            )
            self.assertTrue(form.is_valid())


class TestCreateNewsForm(TestCase):
    def test_field_validation(self):
        message_field_name = "message"
        level_field_name = "level"

        # Fields are empty
        message = ""
        level = ""
        form = forms.CreateNewsForm(
            data={
                message_field_name: message,
                level_field_name: level,
            }
        )
        self.assertTrue(
            "This field is required." in form.errors[message_field_name]
        )
        self.assertTrue(
            "This field is required." in form.errors[level_field_name]
        )

        # Fields are invalid
        max_length = 100
        extra_length = max_length + 1
        message = "a" * extra_length
        level = "invalid_level"
        form = forms.CreateNewsForm(
            data={
                message_field_name: message,
                level_field_name: level,
            }
        )
        self.assertTrue(
            f"Ensure this value has at most 100 characters (it has {extra_length})."
            in form.errors[message_field_name]
        )
        self.assertTrue(
            f"Invalid level {level}." in form.errors[level_field_name]
        )

        # Fields are valid
        message = "a" * max_length
        for status_choice in News.STATUS_CHOICES:
            level = status_choice[0]
            form = forms.CreateNewsForm(
                data={
                    message_field_name: message,
                    level_field_name: level,
                }
            )
            self.assertTrue(form.is_valid())


class TestSetUserRoleForm(TestCase):
    def test_field_validation(self):
        user_id_field_name = "user_id"
        role_field_name = "role"

        # Fields are empty
        user_id = ""
        role = ""
        form = forms.SetUserRoleForm(
            data={
                user_id_field_name: user_id,
                role_field_name: role,
            }
        )
        self.assertTrue(
            "This field is required." in form.errors[user_id_field_name]
        )
        self.assertTrue(
            "This field is required." in form.errors[role_field_name]
        )

        # Fields are invalid
        user_id = "fake_user_id"
        role = "invalid_role"
        form = forms.SetUserRoleForm(
            data={
                user_id_field_name: user_id,
                role_field_name: role,
            }
        )
        self.assertTrue(
            f"User with id {user_id} does not exist."
            in form.errors[user_id_field_name]
        )
        self.assertTrue(
            f"Invalid role {role}." in form.errors[role_field_name]
        )

        # Fields are valid
        user_id = "real_user_id"
        user = User(username=user_id)
        user.set_password("password")
        user.save()
        for role_choice in models.Role.choices():
            role = role_choice[0]
            form = forms.SetUserRoleForm(
                data={
                    user_id_field_name: user_id,
                    role_field_name: role,
                }
            )
            self.assertTrue(form.is_valid())
