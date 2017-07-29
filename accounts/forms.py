"""
This module contains the definition for the forms used for registration and 
account editing.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegistrationForm(UserCreationForm):
    """
    Simple :py:class:`UserCreationForm` subclass that exposes additional
    fields compared to the default.
    """
    first_name = forms.CharField(max_length=32, required=True)
    last_name = forms.CharField(max_length=32, required=True)

    class Meta:
        model = User
        fields = (
            'first_name', 'last_name',
            'username', 'email',
            'password1', 'password2'
        )
