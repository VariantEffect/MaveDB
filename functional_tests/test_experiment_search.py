
"""
Functional testing suite that will test that experiments can be searched
by each database field correctly using the column-wise search boxes
and that advanced search functions as expected.
"""
import datetime

from .base import FunctionalTest
from main.models import Experiment


class SearchFunctionalityTest(FunctionalTest):

    def setUp(self):
        # Setup some simple database entries
        FunctionalTest.setUp(self)
        
        # Populate the databae
        self.exp_item_1 = Experiment.objects.create(
            accession="EXP0000HSA",
            target="BRCA1",
            description="Farva's first experiment.",
            date=datetime.date(2017, 7, 1),
            author="Farva Steelbeard",
            reference="Human",
            alt_reference="Rabit",
            scoring_method="OLS Regression",
            keywords="Kinase, DNA Repair",
            num_variants=125
        )
        self.exp_item_2 = Experiment.objects.create(
            accession="EXP0001MUS",
            target="EGFR",
            date=datetime.date(2017, 7, 5),
            author="Farva Steelbeard",
            description="Farva's second experiment.",
            reference="Mouse",
            alt_reference="Human",
            scoring_method="Log Ratios",
            keywords="Kinase, Energy Production",
            num_variants=100
        )
        self.exp_item_3 = Experiment.objects.create(
            accession="EXP0003HSA",
            target="BRCA2",
            date=datetime.date(2017, 7, 2),
            description="Bertha's first experiment.",
            author="Bertha Agustus",
            reference="Bovine",
            alt_reference="Rabit",
            scoring_method="WLS Regression",
            keywords="Disease, DNA Repair",
            num_variants=98
        )

    def test_crispy_forms_render(self):
        # After a long night of partying to forget heavy blows from the recent
        # crypto-currency crash, Farva decides to check on his experiment
        # submissions. He points the browser to the search view and wonders
        # if today is one of those basic search days or advanced search days.
        self.browser.get(self.live_server_url)
        self.browser.set_window_size(1024, 768)

    def test_basic_search_functions_as_expected(self):
        pass

    def test_advanced_search_functions_as_expected(self):
        pass
