"""
This module contains the definition for the forms used for registration and 
account editing.
"""

import logging

from django import forms
from django.utils.translation import ugettext as _
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from core.utilities import is_null

from guardian.conf.settings import ANONYMOUS_USER_NAME

from search.forms import parse_char_list

from .models import Profile
from .mixins import UserFilterMixin
from .permissions import (
    GroupTypes,
    user_is_anonymous,
    update_admin_list_for_instance,
    update_editor_list_for_instance,
    update_viewer_list_for_instance,
    valid_model_instance,
    valid_group_type
)


User = get_user_model()
logger = logging.getLogger("django")
user_filter = UserFilterMixin()


class UserSearchForm(forms.Form):
    """Search by text fields and keywords."""
    def __init__(self, *args, **kwargs):
        super(UserSearchForm, self).__init__(*args, **kwargs)
        self.fields['username'] = forms.CharField(
            max_length=None, label="ORCID", required=False,
            initial=None, empty_value="",
            widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.username, i.username)
                    for i in User.objects.all()
                    if not user_is_anonymous(i)
                ]))
            ),
        )
        self.fields['first_name'] = forms.CharField(
            max_length=None, label="First name", required=False,
            initial=None, empty_value="",
            widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.first_name, i.first_name)
                    for i in User.objects.all()
                    if not user_is_anonymous(i)
                ]))
            ),
        )
        self.fields['last_name'] = forms.CharField(
            max_length=None, label="Last name", required=False,
            initial=None, empty_value="",
            widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.last_name, i.last_name)
                    for i in User.objects.all()
                    if not user_is_anonymous(i)
                ]))
            ),
        )

    def clean_first_name(self):
        field_name = 'first_name'
        instances = parse_char_list(self.cleaned_data.get(field_name, []))
        return list(set([i for i in instances if not is_null(i)]))

    def clean_last_name(self):
        field_name = 'last_name'
        instances = parse_char_list(self.cleaned_data.get(field_name, []))
        return list(set([i for i in instances if not is_null(i)]))

    def clean_username(self):
        field_name = 'username'
        instances = parse_char_list(self.cleaned_data.get(field_name, []))
        return list(set([i for i in instances if not is_null(i)]))

    def make_filters(self, join=True):
        data = self.cleaned_data
        search_dict = {
            'first_name': data.get('first_name', ""),
            'last_name': data.get('last_name', ""),
            'username': data.get('username', ""),
        }
        join_func = None
        if join:
            join_func = user_filter.or_join_qs
        return user_filter.search_all(search_dict, join_func=join_func)


class SelectUsersForm(forms.Form):
    """
    This form contains a single :py:class:`forms.ModelMultipleChoiceField`
    field which displays a html select widget that an administrator can
    choose users from to add/remove to/from a permission group. The submitted
    input are the primary keys of users in string format and after the clean
    process is run, this list is turned into a list of valid user instances.

    Superusers will always be added back as an admin so errors messages
    are not shown if the requesting user is a SU.

    Parameters
    ----------
    user : `User`:
        The request user.

    group : str
        A valid string from :class:`GroupType`

    instance : :class:`ExperimentSet`, :class:`Experiment` or :class:`ScoreSet`
        An instance for which the permissions are being altered.

    required : bool, optional. Default: False
        Specify whether the form field should be required.abs

    Methods
    -------
    clean
        Overrides the base class to additionally check if an assignment
        will result in no administrators.

    process_user_list
        Defers the call to the appropriate update function for the input
        user list based on the initialised group type.
    """
    users = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.SelectMultiple(
            attrs={
                "class": "select2 select2-token-select",
                "style": "width:100%;height:50px;"
            }
        ),
        error_messages={
            'list': _('Enter a list of values.'),
            'invalid_pk_value': _('User "%(pk)s" does not exist.')
        }
    )

    def __init__(self, user, group, instance, required=False, *args, **kwargs):
        if not valid_group_type(group):
            raise ValueError("Unrecognised group type {}".format(group))
        if not valid_model_instance(instance):
            raise ValueError("Unrecognised instance type {}".format(
                instance.__class__.__name__
            ))

        if instance is not None:
            if group == GroupTypes.ADMIN:
                initial = [u.pk for u in instance.administrators()]
                kwargs["initial"] = {"users": initial}
            elif group == GroupTypes.EDITOR:
                initial = [u.pk for u in instance.editors()]
                kwargs["initial"] = {"users": initial}
            elif group == GroupTypes.VIEWER:
                initial = [u.pk for u in instance.viewers()]
                kwargs["initial"] = {"users": initial}

        super(SelectUsersForm, self).__init__(*args, **kwargs)
        self.fields["users"].queryset = User.objects.exclude(
            username=ANONYMOUS_USER_NAME
        )
        self.fields["users"].choices = [(u.pk, u.profile.unique_name)
             for u in self.fields["users"].queryset]

        self.user = user
        self.fields["users"].required = required
        self.group = group
        self.instance = instance

    def clean(self):
        cleaned_data = super(SelectUsersForm, self).clean()
        users = cleaned_data.get("users", None)

        if users is not None:
            users = users.filter(is_superuser=False)
            if self.group == GroupTypes.ADMIN and users.count() == 0:
                if not self.user.is_superuser:
                    raise ValidationError(
                        _("There must be at least one administrator.")
                    )

        if users is not None:
            if self.group in [GroupTypes.EDITOR, GroupTypes.VIEWER]:
                admins = self.instance.administrators().filter(
                    is_superuser=False)
                if admins.count() == 1 and admins[0] in users:
                    if not self.user.is_superuser:
                        raise ValidationError(
                            _(
                                "Cannot assign the only administrator "
                                "to another group."
                            )
                        )
        return cleaned_data

    def process_user_list(self):
        """
        Defer the call to the appropriate update function for the input
        user list based on the initialised group type.
        """
        existing_admins = self.instance.administrators()
        existing_editors = self.instance.editors()
        existing_viewers = self.instance.viewers()
        user_reassigned = {}

        if self.is_bound and self.is_valid():
            users = self.clean().get("users", [])
            if self.group == GroupTypes.ADMIN:
                existing = existing_admins
                for user in users:
                    if user in existing_editors or existing_viewers:
                        user_reassigned[user] = True
                update_admin_list_for_instance(users, self.instance)

            elif self.group == GroupTypes.EDITOR:
                existing = existing_editors
                for user in users:
                    if user in existing_admins or existing_viewers:
                        user_reassigned[user] = True
                update_editor_list_for_instance(users, self.instance)

            elif self.group == GroupTypes.VIEWER:
                existing = existing_viewers
                for user in users:
                    if user in existing_admins or existing_editors:
                        user_reassigned[user] = True
                update_viewer_list_for_instance(users, self.instance)

            else:
                raise ValueError("Unrecognised group '{}'".format(self.group))

            for user in existing:
                if user not in users:
                    user.profile.notify_user_group_change(
                        instance=self.instance,
                        action='removed', group=self.group
                    )
            for user in users:
                reassigned = user_reassigned.get(user, False)
                if reassigned:
                    user.profile.notify_user_group_change(
                        instance=self.instance,
                        action='re-assigned', group=self.group
                    )
                else:
                    if user not in existing:
                        user.profile.notify_user_group_change(
                            instance=self.instance,
                            action='added', group=self.group
                        )


class RegistrationForm(UserCreationForm):
    """
    Simple :py:class:`UserCreationForm` subclass that exposes additional
    fields compared to the default.
    """
    class Meta:
        model = User
        fields = (
            'username', 'email',
            'password1', 'password2'
        )


class ProfileForm(forms.ModelForm):
    """Simple form for setting an email address."""
    class Meta:
        model = Profile
        fields = ('email',)
        help_texts = {
            'email': (
                'You can provide an alternative email address below. We will '
                'use this email over your ORCID email to '
                'contact you.'
            )
        }
