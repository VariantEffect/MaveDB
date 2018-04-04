"""
genome.factories
=================

This module contains factory methods for creating test fixtures. If there are
any updates to the models which will have an impact on the tests, then they
can be changed once here instead of throughout all the tests. This will help
with future maintainability.
"""

import factory.fuzzy
from factory.django import DjangoModelFactory

from .models import TargetOrganism


class TargetOrganismFactpry(DjangoModelFactory):
    """
    Factory for creating simple minimally instantiated :class:`TargetOrganism`
    instances.
    """
    class Meta:
        model = TargetOrganism

    text = factory.fuzzy.FuzzyText(length=12)
