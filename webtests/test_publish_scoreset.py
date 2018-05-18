from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

from django.test import LiveServerTestCase, mock

from accounts.factories import UserFactory

from dataset import models as data_models
from dataset import factories as data_factories
from dataset import tasks
from dataset import constants

from variant.factories import VariantFactory

from .utilities import authenticate_webdriver


class TestPublishScoreSet(LiveServerTestCase):
    
    def setUp(self):
        self.user = UserFactory()
        self.browser = webdriver.Firefox()
    
    def authenticate(self):
        authenticate_webdriver(
            self.user.username, self.user._password, self, 'browser')
    
    def test_edit_blocked_if_scs_is_in_processing_state(self):
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
    
        # Check dashboard to see if error message is shown
        messages = self.browser.find_elements_by_class_name('alert-danger')
        self.assertEqual(len(messages), 1)
        self.assertIn(
            'being processed cannot be edited.',
            messages[0].text
        )

    def test_publish_limits_edit_fields(self):
        scoreset = data_factories.ScoreSetWithTargetFactory()
        scoreset.add_administrators(self.user)
        scoreset.publish()

        self.authenticate()
        self.browser.get(
            self.live_server_url +
            '/profile/edit/scoreset/{}/'.format(scoreset.urn)
        )
        self.assertTrue(scoreset.has_public_urn)
        self.assertTrue(scoreset.parent.has_public_urn)
        self.assertTrue(scoreset.parent.parent.has_public_urn)
        
        # Should not be able to find fields such as experiment, replaces
        # and file uploads
        with self.assertRaises(NoSuchElementException):
            self.browser.find_element_by_id("id_score_data")
            self.browser.find_element_by_id("id_count_data")
            self.browser.find_element_by_id("id_meta_data")
            self.browser.find_element_by_id("id_experiment")
            self.browser.find_element_by_id("id_replaces")
            self.browser.find_element_by_id("id_name")
            self.browser.find_element_by_id("id_wt_sequence")
            self.browser.find_element_by_id("id_genome")
            self.browser.find_element_by_id("id_uniprot-identifier")
            self.browser.find_element_by_id("id_refseq-identifier")
            self.browser.find_element_by_id("id_ensembl-identifier")
            self.browser.find_element_by_id("id_uniprot-offset")
            self.browser.find_element_by_id("id_refseq-offset")
            self.browser.find_element_by_id("id_ensembl-offset")
            
            
    @mock.patch('core.tasks.email_admins.delay')
    @mock.patch('dataset.tasks.publish_scoreset.delay')
    def test_publish_updates_states(self, publish_patch, email_patch):
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
        self.browser.get(
            self.live_server_url + '/profile/'
        )
        icon = self.browser.find_element_by_class_name('processing-icon')
        self.assertIsNotNone(icon)

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
            
        self.browser.get(
            self.live_server_url + '/profile/'
        )
        icon = self.browser.find_element_by_class_name('success-icon')
        self.assertIsNotNone(icon)
    
    def test_no_delete_icon_for_public_entry(self):
        scoreset = data_factories.ScoreSetWithTargetFactory()
        scoreset.publish()
        scoreset.add_administrators(self.user)
        scoreset.experiment.add_administrators(self.user)
        scoreset.experiment.experimentset.add_administrators(self.user)

        icons = self.browser.find_elements_by_class_name('trash-icon')
        self.assertEqual(len(icons), 0)
