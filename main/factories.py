from datetime import datetime

import factory
import factory.fuzzy
from factory.django import DjangoModelFactory

from .models import SiteInformation, News


class SiteInformationFactory(DjangoModelFactory):
    """
    Factory for producing test instances for :class:`SiteInformation`.
    """

    class Meta:
        model = SiteInformation

    md_about = factory.faker.Faker("text", max_nb_chars=1500)
    md_citation = factory.faker.Faker("text", max_nb_chars=1500)
    md_usage_guide = factory.faker.Faker("text", max_nb_chars=250)
    md_documentation = factory.faker.Faker("text", max_nb_chars=1000)
    md_terms = factory.faker.Faker("text", max_nb_chars=1000)
    md_privacy = factory.faker.Faker("text", max_nb_chars=1000)
    email = factory.faker.Faker("email")
    version = "1.0"
    version_date = datetime.now()
    branch = "master"


class NewsFactory(DjangoModelFactory):
    """
    Factory for producing test instances for :class:`SiteInformation`.
    """

    class Meta:
        model = News

    text = factory.faker.Faker("text", max_nb_chars=500)
    level = factory.fuzzy.FuzzyChoice([x[1] for x in News.STATUS_CHOICES])
