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

from django.contrib.auth.models import User
from django.contrib.auth.models import AnonymousUser

from .models import Profile


def AnonymousUserFactory():
    """
    Create an anonymous user from :class:`AnonymousUser`.
    """
    return AnonymousUser()


def UserFactory(username=None, password=None, first_name=None,
                last_name=None):
    """
    Test fixture factory for the user class which sets username,
    first_name, last_name and password.
    """
    if username is None:
        username = factory.fuzzy.FuzzyText(length=8).fuzz()
    if password is None:
        password = factory.fuzzy.FuzzyText(length=16).fuzz()
    if first_name is None:
        first_name = factory.fuzzy.FuzzyChoice(
            ['Spike', 'Jet', 'Faye', 'Ed', 'Ein']).fuzz()
    if last_name is None:
        last_name = factory.fuzzy.FuzzyChoice(
            ['Spiegel', 'Black', 'Valentine', 'Ed', 'Ein']).fuzz()

    return User.objects.create(
        username=username,
        password=password,
        first_name=first_name,
        last_name=last_name
    )


def ProfileFactory(user=None):
    """
    Test fixture factory for creating a profile linked to a randomly
    genreated user.
    """
    if user is None:
        user = UserFactory()
    return Profile.objects.create(user=user)
