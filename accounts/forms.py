"""
This module contains the definition for the forms used for registration and 
account editing.
"""

from django import forms

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from django.core.mail import send_mail

from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string

from .tokens import account_activation_token


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
