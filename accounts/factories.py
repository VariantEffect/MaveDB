"""
accounts.factories
=================

This module contains factory methods for creating test fixtures for
:class:`User` and :class:`Profile`. If there are
any updates to the models which will have an impact on the tests, then they
can be changed once here instead of throughout all the tests. This will help
with future maintainability.
"""

import factory.fuzzy
from factory.django import DjangoModelFactory

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from .models import Profile


class AnonymousUserFactory:
    """
    Create an anonymous user from :class:`AnonymousUser`.
    """
    def __call__(self, *args, **kwargs):
        return AnonymousUser()


class UserFactory(DjangoModelFactory):
    """
    Test fixture factory for the user class which sets username,
    first_name, last_name and password.
    """
    class Meta:
        model = get_user_model()

    username = factory.fuzzy.FuzzyText(length=8)
    password = factory.fuzzy.FuzzyText(length=16)
    first_name = factory.fuzzy.FuzzyChoice(
        ['Spike', 'Jet', 'Faye', 'Ed', 'Ein'])
    last_name = factory.fuzzy.FuzzyChoice(
        ['Spiegel', 'Black', 'Valentine', 'Ed', 'Ein'])


class ProfileFactory(DjangoModelFactory):
    """
    Test fixture factory for creating a profile linked to a randomly
    genreated user.
    """
    class Meta:
        model = Profile

    user = UserFactory()
