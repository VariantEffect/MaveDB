import os
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import ElementNotInteractableException

from django.test import LiveServerTestCase, mock

from accounts.factories import UserFactory

from dataset import models as data_models
from dataset import factories as data_factories
from dataset import tasks
from dataset import constants

from metadata import models as meta_models
from metadata import factories as meta_factories

from variant.factories import VariantFactory

from .utilities import authenticate_webdriver


class TestCreateExperimentAndScoreSet(LiveServerTestCase):
    
    def setUp(self):
        self.user = UserFactory()
        self.browser = webdriver.Firefox()
    
    def authenticate(self):
        authenticate_webdriver(
            self.user.username, self.user._password, self, 'browser')
    
    def test_cannot_publish_no_variants(self):
        scoreset = data_factories.ScoreSetWithTargetFactory()
        scoreset.experiment.add_administrators(self.user)
        scoreset.add_administrators(self.user)
        self.authenticate()
        self.browser.get(
            self.live_server_url +
            '/profile/edit/scoreset/{}/'.format(scoreset.urn)
        )
        
        # Try publishing
        submit = self.browser.find_element_by_id('publish-form')
        submit.click()

        # Check dashboard to see if error message is shown
        messages = self.browser.find_elements_by_class_name('invalid-feedback')
        self.assertEqual(len(messages), 1)
        self.assertEqual(
            messages[0].text, 'You must upload a non-empty scores data file.')

    def test_upload_files_blocked_if_scs_is_in_processing_state(self):
        scoreset = data_factories.ScoreSetWithTargetFactory()
        scoreset.experiment.add_administrators(self.user)
        scoreset.add_administrators(self.user)
        scoreset.processing_state = constants.processing
        scoreset.save()
        self.authenticate()
        self.browser.get(
            self.live_server_url +
            '/profile/edit/scoreset/{}/'.format(scoreset.urn)
        )
    
        # Upload a local file.
        with self.assertRaises(ElementNotInteractableException):
            self.browser.find_element_by_id("id_score_data").\
                send_keys(os.getcwd() + "/webtests/scores.csv")
        with self.assertRaises(ElementNotInteractableException):
            self.browser.find_element_by_id("id_count_data").\
                send_keys(os.getcwd() + "/webtests/scores.csv")

    @mock.patch('dataset.tasks.create_variants.delay')
    def test_publish_limits_edit_fields(self, variants_patch):
        scoreset = data_factories.ScoreSetWithTargetFactory()
        scoreset.experiment.add_administrators(self.user)
        scoreset.add_administrators(self.user)
        scoreset.processing_state = constants.processing
        scoreset.save()
        self.authenticate()
        self.browser.get(
            self.live_server_url +
            '/profile/edit/scoreset/{}/'.format(scoreset.urn)
        )
    
        # Upload a local file.
        self.browser.find_element_by_id("id_score_data"). \
            send_keys(os.getcwd() + "/webtests/scores.csv")
        
        # Try publishing
        submit = self.browser.find_element_by_id('publish-form')
        submit.click()
        
        messages = self.browser.find_elements_by_class_name('alert-success')
        self.assertEqual(len(messages), 1)
        
        variants_patch.assert_called()
        tasks.create_variants(**variants_patch.call_args[1])
        
        scoreset.refresh_from_db()
        self.assertTrue(scoreset.has_public_urn)
        self.assertTrue(scoreset.parent.has_public_urn)
        self.assertTrue(scoreset.parent.parent.has_public_urn)

    @mock.patch('core.tasks.email_admins.delay')
    @mock.patch('dataset.tasks.publish_scoreset.delay')
    def test_publish_without_uploading_new_file(self, publish_patch, email_patch):
        scoreset = data_factories.ScoreSetWithTargetFactory()
        scoreset.experiment.add_administrators(self.user)
        scoreset.add_administrators(self.user)
        scoreset.save()
        
        # Add some variants
        VariantFactory(scoreset=scoreset)
        
        self.authenticate()
        self.browser.get(
            self.live_server_url +
            '/profile/edit/scoreset/{}/'.format(scoreset.urn)
        )
        
        # Try publishing
        submit = self.browser.find_element_by_id('publish')
        submit.click()
        self.browser.switch_to.alert.accept()

        # Should be in processing state
        scoreset.refresh_from_db()
        self.assertEqual(scoreset.processing_state, constants.processing)
        
        # Manually invoke the task
        publish_patch.assert_called()
        tasks.publish_scoreset(**publish_patch.call_args[1])
        email_patch.assert_called()
        
        # Check to see if the publish worked
        scoreset = data_models.scoreset.ScoreSet.objects.first()
        self.assertTrue(scoreset.has_public_urn)
        self.assertTrue(scoreset.parent.has_public_urn)
        self.assertTrue(scoreset.parent.parent.has_public_urn)
        for variant in scoreset.children:
            self.assertTrue(variant.has_public_urn)
            
    