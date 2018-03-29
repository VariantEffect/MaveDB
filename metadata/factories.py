"""
dataset.factories
=================

This module contains factory methods for creating test fixtures for
:class:`keyword` and subclasses of :class:`ExternalIdentifier`. If there are
any updates to the models which will have an impact on the tests, then they
can be changed once here instead of throughout all the tests. This will help
with future maintainability.
"""

import factory.fuzzy
from factory.django import DjangoModelFactory

from .models import Keyword, SraIdentifier, DoiIdentifier, PubmedIdentifier


class KeywordFactory(DjangoModelFactory):
    """Factory creating a keyword with a random `text` attribute."""
    class Meta:
        model = Keyword

    text = factory.fuzzy.FuzzyText(length=10)


class SraIdentifierFactory(DjangoModelFactory):
    """
    Factory creating :class:`SraIdentifier` instances matching the
    SRA_RUN_PATTERN
    """
    class Meta:
        model = SraIdentifier

    identifier = factory.fuzzy.FuzzyChoice([
        'SRX3407687', 'SRX3407686', 'SRX366265', 'PRJNA419207', 'PRJNA362734'
    ])


class DoiIdentifierFactory(DjangoModelFactory):
    """
    Factory creating :class:`DoiIdentifier` instances with a random choice
    of doi ids.
    """

    class Meta:
        model = DoiIdentifier

    identifier = factory.fuzzy.FuzzyChoice([
        '10.1016/j.cels.2018.01.015',
        '10.1016/j.jmb.2018.02.009',
        '10.1038/s41598-017-17081-y.',
        '10.1007/978-1-4939-7366-8_6',
        '10.1073/pnas.1614437114'
    ])


class PubmedIdentifierFactory(DjangoModelFactory):
    """
    Factory creating :class:`PubmedIdentifier` instances with a random choice
    of ids.
    """

    class Meta:
        model = PubmedIdentifier

    identifier = factory.fuzzy.FuzzyChoice([
        '29086305', '29103961', '29269382', '29415752', '29525204'
    ])