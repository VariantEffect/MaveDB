"""
This module contains the definition for the forms used for registration and 
account editing.
"""

from django import forms

from django.utils.translation import ugettext as _
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from django.core.mail import send_mail
from django.core.exceptions import ValidationError

from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string

from guardian.conf.settings import ANONYMOUS_USER_NAME

from .tokens import account_activation_token
from .permissions import (
    GroupTypes,
    update_admin_list_for_instance,
    update_contributor_list_for_instance,
    update_viewer_list_for_instance,
    valid_model_instance,
    valid_group_type
)


class SelectUsersForm(forms.Form):
    users = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.SelectMultiple(
            attrs={
                "class": "select2 select2-token-select",
                "style": "width:100%;height:50px;"
            }
        )
    )

    def process_user_list(self):
        users = self.clean().get("users", [])
        if self.group == GroupTypes.ADMIN:
            update_admin_list_for_instance(users, self.instance)
        elif self.group == GroupTypes.CONTRIBUTOR:
            update_contributor_list_for_instance(users, self.instance)
        elif self.group == GroupTypes.VIEWER:
            update_viewer_list_for_instance(users, self.instance)

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

    def __init__(self, group, instance, required=False, *args, **kwargs):
        super(SelectUsersForm, self).__init__(*args, **kwargs)
        self.fields["users"].queryset = User.objects.exclude(
            username=ANONYMOUS_USER_NAME
        ).exclude(is_superuser=True)
        self.fields["users"].required = required
        if not valid_group_type(group):
            raise ValueError("Unrecognised group type {}".format(group))
        if not valid_model_instance(instance):
            raise ValueError("Unrecognised instance type {}".format(
                instance.__class__.__name__
            ))
        self.group = group
        self.instance = instance


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


def send_user_activation_email(uid, secure, domain, subject, template_name):
    try:
        user = User.objects.get(pk=uid)
    except User.DoesNotExist:
        print("Could not find user {}".format(uid))
        return None, None

    try:
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = account_activation_token.make_token(user)
    except (TypeError, ValueError, OverflowError):
        print("Could not make uidb64/token.")
        return None, None

    message = render_to_string(template_name, {
        'user': user,
        'protocol': 'https' if secure else 'http',
        'domain': domain,
        'uid': uidb64,
        'token': token})
    user.email_user(subject, message)
    return uidb64, token
