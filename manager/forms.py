from django import forms
from django.core.exceptions import ValidationError

from dataset import constants
from main.models import News
from manager.models import Role
from metadata.validators import validate_pubmed_identifier
from urn.validators import validate_mavedb_urn

class AddPmidForm(forms.Form):
    urn = forms.CharField(max_length=100)
    pmid = forms.CharField(max_length=100)

    def clean_urn(self):
        field_name = 'urn'
        urn = self.cleaned_data[field_name]
        try:
            validate_mavedb_urn(urn)
        except ValidationError as e:
            self.add_error(field_name, e)
        return urn

    def clean_pmid(self):
        field_name = 'pmid'
        pmid = self.cleaned_data[field_name]
        try:
            validate_pubmed_identifier(pmid)
        except ValidationError as e:
            self.add_error(field_name, e)
        return pmid


class AddUserForm(forms.Form):
    urn = forms.CharField(max_length=100)
    user_id = forms.CharField(max_length=100)
    role = forms.CharField(max_length=100)

    def clean_urn(self):
        field_name = 'urn'
        urn = self.cleaned_data[field_name]
        try:
            validate_mavedb_urn(urn)
        except ValidationError as e:
            self.add_error(field_name, e)
        return urn

    def clean_user_id(self):
        field_name = 'user_id'
        user_id = self.cleaned_data[field_name]
        return user_id

    def clean_role(self):
        field_name = 'role'
        role = self.cleaned_data[field_name]
        valid_roles = (
            constants.administrator,
            constants.editor,
            constants.viewer,
        )
        if role not in valid_roles:
            self.add_error(field_name, ValueError(f"Invalid user role {role}."))
        return role


class CreateNewsForm(forms.Form):
    message = forms.CharField(max_length=100)
    level = forms.CharField(max_length=100)

    def clean_level(self):
        field_name = 'level'
        level = self.cleaned_data[field_name]
        valid_levels = {status_choice[0] for status_choice in News.STATUS_CHOICES}
        if level not in valid_levels:
            self.add_error(field_name, ValueError(f"Invalid level {level}."))
        return level


class SetUserRoleForm(forms.Form):
    user_id = forms.CharField(max_length=100)
    role = forms.CharField(max_length=100)

    def clean_role(self):
        field_name = 'role'
        role = self.cleaned_data[field_name]
        valid_roles = {r[0] for r in Role.choices()}
        if role not in valid_roles:
            self.add_error(field_name, ValueError(f"Invalid role {role}."))
        return role
