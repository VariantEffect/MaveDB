import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from django.test import LiveServerTestCase

from accounts.factories import UserFactory

from dataset import models as data_models
from dataset import factories as data_factories

from metadata import models as meta_models
from metadata import factories as meta_factories

from .utilities import authenticate_webdriver


class TestCreateExperimentAndScoreSet(LiveServerTestCase):
    
    def mock_data(self):
        return {
            "title": "A new experiment",
            "description": "Hello, world!",
            "pubmed_ids": ['29269382'],
        }
    
    def setUp(self):
        self.user = UserFactory()
        self.browser = webdriver.Firefox()
        
    def authenticate(self):
        authenticate_webdriver(
            self.user.username, self.user._password, self, 'browser')
        
    def test_create_experiment_flow(self):
        # Create some experimentsets that the user should not be able to see
        exps1 = data_factories.ExperimentSetFactory(private=False)
        exps2 = data_factories.ExperimentSetFactory()
        exps3 = data_factories.ExperimentSetFactory()
        exps2.add_administrators(self.user)
        exps3.add_viewers(self.user)
        
        self.authenticate()
        self.browser.get(self.live_server_url + '/experiment/new/')

        exps_select = Select(self.browser.find_element_by_id('id_experimentset'))
        options = [o.text for o in exps_select.options]
        self.assertIn(exps2.urn, options)
        self.assertNotIn(exps1.urn, options)
        self.assertNotIn(exps3.urn, options)
        
        title = self.browser.find_element_by_id('id_title')
        title.send_keys("Experiment 1")
        
        description = self.browser.find_element_by_id('id_short_description')
        description.send_keys("hello, world!")
        
        submit = self.browser.find_element_by_id('submit-form')
        submit.click()
        
        # After creating a new experiment, we should now be at the create
        # scoreset view.
        exps1.delete()
        exps2.delete()
        exps3.delete()
        
        experiment = data_models.experiment.Experiment.objects.first()
        messages = self.browser.find_elements_by_class_name('alert-success')
        self.assertEqual(len(messages), 1)
        self.assertIsNotNone(experiment)
        self.assertFalse(experiment.has_public_urn)
        self.assertIn(
            'scoreset/new/?experiment={}'.format(experiment.urn),
            self.browser.current_url
        )
        
        # Add in some ids to see if they are loaded and selected.
        kw = meta_factories.KeywordFactory()
        pm = meta_factories.PubmedIdentifierFactory()
        doi = meta_factories.DoiIdentifierFactory()
        experiment.add_keyword(kw)
        experiment.add_identifier(pm)
        experiment.add_identifier(doi)
        
        # Refresh the page. And check the correct elements are selected.
        self.browser.refresh()
        exp_select = Select(self.browser.find_element_by_id('id_experiment'))
        self.assertEqual(
            [o.text for o in exp_select.all_selected_options], [experiment.urn]
        )

        kw_select = Select(self.browser.find_element_by_id('id_keywords'))
        self.assertEqual(
            [o.text for o in kw_select.all_selected_options], [kw.text]
        )
        
        pm_select = Select(self.browser.find_element_by_id('id_pubmed_ids'))
        self.assertEqual(
            [o.text for o in pm_select.all_selected_options], [pm.identifier]
        )
        
        doi_select = Select(self.browser.find_element_by_id('id_doi_ids'))
        self.assertEqual(
            [o.text for o in doi_select.all_selected_options], [doi.identifier]
        )
        
        # Check to see if the target drop down will auto-populate fields
        # TODO: Find a way to make the ajax call trigger from Selenium.
        # Edit: Couldn't find a way, might be better to test this with a
        # javascript front end testing framework?
        scs = data_factories.ScoreSetWithTargetFactory()
        scs.add_viewers(self.user)
        self.authenticate()
        self.browser.get(
            self.live_server_url +
            '/scoreset/new/?experiment={}'.format(experiment.urn)
        )
        
        # Fill in the remaining fields
        title = self.browser.find_element_by_id('id_title')
        title.send_keys("Score Set 1")

        description = self.browser.find_element_by_id('id_short_description')
        description.send_keys("hello, new world!")
        
        description = self.browser.find_element_by_id('id_target')
        description.send_keys("hello, new world!")
        
        genome_select = Select(self.browser.find_element_by_id('id_genome'))
        genome_select.select_by_index(1)
        
        # At least check if the target is clickable.
        target_select = Select(self.browser.find_element_by_id('id_target'))
        self.assertEqual(len([o.text for o in target_select.options]), 2)
        self.assertIn(scs.urn, target_select.options[1].text)
        
        target_name = self.browser.find_element_by_id('id_name')
        target_name.send_keys("BRCA1")
        target_seq = self.browser.find_element_by_id('id_wt_sequence')
        target_seq.send_keys("atcg")
        
        # Upload a local file.
        self.browser.find_element_by_id("id_score_data").\
            send_keys(os.getcwd() + "/webtests/scores.csv")
    
        submit = self.browser.find_element_by_id('submit-form')
        submit.click()

        # Check dashboard to see if correct processing state and visibility
        # is set.
        messages = self.browser.find_elements_by_class_name('alert-success')
        self.assertEqual(len(messages), 1)
        

        self.fail()
