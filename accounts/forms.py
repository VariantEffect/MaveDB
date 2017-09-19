"""
This module contains the definition for the forms used for registration and 
account editing.
"""

import logging
from django import forms

from django.utils.translation import ugettext as _
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string

from guardian.conf.settings import ANONYMOUS_USER_NAME

from .permissions import (
    GroupTypes,
    update_admin_list_for_instance,
    update_contributor_list_for_instance,
    update_viewer_list_for_instance,
    valid_model_instance,
    valid_group_type
)

logger = logging.getLogger("django")


class SelectUsersForm(forms.Form):
    """
    This form contains a single :py:class:`forms.ModelMultipleChoiceField`
    field which displays a html select widget that an administrator can
    choose users from to add/remove to/from a permission group. The submitted
    input are the primary keys of users in string format and after the clean
    process is run, this list is turned into a list of valid user instances.

    Parameters
    ----------
    group : `str`
        A valid string from py:class:`GroupType`

    instance : `ExperimentSet`, `Experiment` or `ScoreSet`
        An instance for which the permissions are being altered.

    required : `bool`, optional, default: `False`
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
                "class": "form-control select2 select2-token-select",
                "style": "width:100%;height:50px;"
            }
        )
    )

    def __init__(self, group, instance, required=False, *args, **kwargs):
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
            elif group == GroupTypes.CONTRIBUTOR:
                initial = [u.pk for u in instance.contributors()]
                kwargs["initial"] = {"users": initial}
            elif group == GroupTypes.VIEWER:
                initial = [u.pk for u in instance.viewers()]
                kwargs["initial"] = {"users": initial}

        super(SelectUsersForm, self).__init__(*args, **kwargs)
        self.fields["users"].queryset = User.objects.exclude(
            username=ANONYMOUS_USER_NAME
        ).exclude(is_superuser=True)
        self.fields["users"].required = required
        self.group = group
        self.instance = instance

    def clean(self):
        cleaned_data = super(SelectUsersForm, self).clean()
        users = cleaned_data.get("users", None)

        if users is not None:
            if self.group == GroupTypes.ADMIN and users.count() == 0:
                raise ValidationError(
                    _("There must be at least one administrator.")
                )

        if users is not None:
            if self.group in [GroupTypes.CONTRIBUTOR, GroupTypes.VIEWER]:
                admins = self.instance.administrators()
                if admins.count() == 1 and admins[0] in users:
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
        if self.is_bound and self.is_valid():
            users = self.clean().get("users", [])
            if self.group == GroupTypes.ADMIN:
                update_admin_list_for_instance(users, self.instance)
            elif self.group == GroupTypes.CONTRIBUTOR:
                update_contributor_list_for_instance(users, self.instance)
            elif self.group == GroupTypes.VIEWER:
                update_viewer_list_for_instance(users, self.instance)


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


def send_admin_email(user, instance):
    """
    Sends an email to all admins.

    Parameters
    ----------
    user : `auth.User`
        The user who created the instance.
    instance : `object`
        The instance created.

    """
    template_name = "accounts/alert_admin_new_entry_email.html"
    admins = User.objects.filter(is_superuser=True)
    message = render_to_string(template_name, {
        'user': user,
        'instance': instance,
        'class_name': instance.__class__.__name__
    })

    subject = "[MAVEDB ADMIN] New entry requires your attention."
    for admin in admins:
        logger.warning("Sending email to {}".format(admin.username))
        admin.email_user(subject, message)
