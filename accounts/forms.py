"""
This module contains the definition for the forms used for registration and 
account editing.
"""

import logging

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

from core.utilities import is_null

from search.forms import parse_char_list

from .models import Profile
from .mixins import UserFilterMixin, filter_anon
from .permissions import (
    GroupTypes,
    user_is_anonymous,
    update_admin_list_for_instance,
    update_editor_list_for_instance,
    update_viewer_list_for_instance,
    valid_model_instance,
)


User = get_user_model()
logger = logging.getLogger("django")
user_filter = UserFilterMixin()


class ConfirmationForm(forms.Form):
    pass


class UserSearchForm(forms.Form):
    """Search by text fields and keywords."""
    def __init__(self, *args, **kwargs):
        super(UserSearchForm, self).__init__(*args, **kwargs)
        self.fields[user_filter.USERNAME] = forms.CharField(
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
        self.fields[user_filter.FIRST_NAME] = forms.CharField(
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
        self.fields[user_filter.LAST_NAME] = forms.CharField(
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
        field_name = user_filter.FIRST_NAME
        instances = parse_char_list(self.cleaned_data.get(field_name, []))
        return list(set([i for i in instances if not is_null(i)]))

    def clean_last_name(self):
        field_name = user_filter.LAST_NAME
        instances = parse_char_list(self.cleaned_data.get(field_name, []))
        return list(set([i for i in instances if not is_null(i)]))

    def clean_username(self):
        field_name = user_filter.USERNAME
        instances = parse_char_list(self.cleaned_data.get(field_name, []))
        return list(set([i for i in instances if not is_null(i)]))

    def make_filters(self, join=True):
        data = self.cleaned_data
        search_dict = {
            user_filter.FIRST_NAME: data.get(user_filter.FIRST_NAME, ""),
            user_filter.LAST_NAME: data.get(user_filter.LAST_NAME, ""),
            user_filter.USERNAME: data.get(user_filter.USERNAME, ""),
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
    administrators = forms.ModelMultipleChoiceField(
        queryset=None,
        required=True,
        label='Administrators',
        widget=forms.SelectMultiple(
            attrs={
                "class": "select2 select2-token-select",
                "style": "width:100%;height:50px;"
            }
        ),
        error_messages={
            'list': 'Enter a list of values.',
            'invalid_pk_value': 'User "%(pk)s" does not exist.',
        }
    )
    editors = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        label='Editors',
        widget=forms.SelectMultiple(
            attrs={
                "class": "select2 select2-token-select",
                "style": "width:100%;height:50px;"
            }
        ),
        error_messages={
            'list': 'Enter a list of values.',
            'invalid_pk_value': 'User "%(pk)s" does not exist.',
        }
    )
    viewers = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        label='Viewers',
        widget=forms.SelectMultiple(
            attrs={
                "class": "select2 select2-token-select",
                "style": "width:100%;height:50px;"
            }
        ),
        error_messages={
            'list': 'Enter a list of values.',
            'invalid_pk_value': 'User "%(pk)s" does not exist.',
        }
    )

    def __init__(self, instance, *args, **kwargs):
        if not valid_model_instance(instance):
            raise ValueError("Unrecognised instance type {}".format(
                instance.__class__.__name__
            ))
        
        self.instance = instance
        if instance is not None:
            kwargs["initial"] = {
                "administrators": [u.pk for u in instance.administrators()],
                "editors": [u.pk for u in instance.editors()],
                "viewers": [u.pk for u in instance.viewers()],
            }

        super(SelectUsersForm, self).__init__(*args, **kwargs)

        self.fields['administrators'].queryset = filter_anon(
            User.objects.exclude(is_superuser=True))
        self.fields['editors'].queryset = filter_anon(
            User.objects.exclude(is_superuser=True))
        self.fields['viewers'].queryset = filter_anon(
            User.objects.exclude(is_superuser=True))
        
        self.fields["administrators"].choices = [(u.pk, u.profile.unique_name)
             for u in self.fields["administrators"].queryset]
        self.fields["editors"].choices = [(u.pk, u.profile.unique_name)
             for u in self.fields["editors"].queryset]
        self.fields["viewers"].choices = [(u.pk, u.profile.unique_name)
             for u in self.fields["viewers"].queryset]
        
    def clean(self):
        cleaned_data = super(SelectUsersForm, self).clean()
        administrators = cleaned_data.get("administrators", [])
        editors = cleaned_data.get("editors", [])
        viewers = cleaned_data.get("viewers", [])
        
        if not administrators:
            self.add_error(
                'administrators',
                "There must be at least one administrator."
            )
        for user in administrators:
            if user in editors or user in viewers:
                self.add_error(
                    'administrators',
                    'User \'{user}\' can only be assigned to one group.'.format(
                        user=user.profile.unique_name
                    )
                )
        for user in editors:
            if user in administrators or user in viewers:
                self.add_error(
                    'editors',
                    'User \'{user}\' can only be assigned to one group.'.format(
                        user=user.profile.unique_name
                    )
                )
        for user in viewers:
            if user in administrators or user in editors:
                self.add_error(
                    'viewers',
                    'User \'{user}\' can only be assigned to one group.'.format(
                        user=user.profile.unique_name
                    )
                )
        return cleaned_data

    def process_user_list(self):
        """
        Defer the call to the appropriate update function for the input
        user list based on the initialised group type.
        """
        if not self.is_valid():
            raise ValueError("Cannot process an invalid management form.")
        
        existing_administrators = self.instance.administrators()
        existing_editors = self.instance.editors()
        existing_viewers = self.instance.viewers()
        existing_users = {}
        
        for user in existing_administrators:
            existing_users[user] = GroupTypes.ADMIN
        for user in existing_editors:
            existing_users[user] = GroupTypes.EDITOR
        for user in existing_viewers:
            existing_users[user] = GroupTypes.VIEWER
            
        new_administrators = self.cleaned_data.get('administrators', None)
        new_editors = self.cleaned_data.get('editors', [])
        new_viewers = self.cleaned_data.get('viewers', [])
        reassigned_users = {}
        new_users = {}

        for user in new_administrators:
            if user in existing_editors or existing_viewers:
                reassigned_users[user] = GroupTypes.ADMIN
            new_users[user] = GroupTypes.ADMIN
        for user in new_editors:
            if user in existing_administrators or existing_viewers:
                reassigned_users[user] = GroupTypes.EDITOR
            new_users[user] = GroupTypes.EDITOR
        for user in new_viewers:
            if user in existing_administrators or existing_editors:
                reassigned_users[user] = GroupTypes.VIEWER
            new_users[user] = GroupTypes.VIEWER
        
        update_admin_list_for_instance(new_administrators, self.instance)
        update_editor_list_for_instance(new_editors, self.instance)
        update_viewer_list_for_instance(new_viewers, self.instance)
        
        for user, group in existing_users.items():
            if user not in new_users:
                user.profile.notify_user_group_change(
                    instance=self.instance,
                    action='removed', group=group
                )
            elif user in reassigned_users:
                new_group = reassigned_users[user]
                user.profile.notify_user_group_change(
                    instance=self.instance,
                    action='re-assigned', group=new_group
                )
        for user, group in new_users.items():
            reassigned = reassigned_users.get(user, False)
            if not reassigned and user not in existing_users:
                user.profile.notify_user_group_change(
                    instance=self.instance,
                    action='added', group=group
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
