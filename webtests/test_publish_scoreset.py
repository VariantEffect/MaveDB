from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.firefox.options import FirefoxBinary, Options

from django.test import LiveServerTestCase, mock

from mavedb import celery_app

from accounts.factories import UserFactory

from dataset import models as data_models
from dataset import factories as data_factories
from dataset import tasks
from dataset import constants
from dataset import utilities

from variant.factories import VariantFactory

from .utilities import (
    authenticate_webdriver,
    LOG_PATH,
    STAGING_OR_PROD,
    ActionMixin,
)

celery_app.conf["task_always_eager"] = False


class TestPublishScoreSet(LiveServerTestCase, ActionMixin):
    def setUp(self):
        self.user = UserFactory()
        if STAGING_OR_PROD:
            binary = FirefoxBinary("/usr/bin/firefox")
            options = Options()
            options.add_argument("--headless")
        else:
            binary = None
            options = None
        self.browser = webdriver.Firefox(
            log_path=LOG_PATH, firefox_options=options, firefox_binary=binary
        )

    def tearDown(self):
        self.browser.close()

    def authenticate(self):
        authenticate_webdriver(
            self.user.username, self.user._password, self, "browser"
        )

    def test_edit_blocked_if_scs_is_in_processing_state(self):
        scoreset = data_factories.ScoreSetWithTargetFactory()
        scoreset.experiment.add_administrators(self.user)
        scoreset.add_administrators(self.user)
        scoreset.processing_state = constants.processing
        scoreset.save()
        self.authenticate()
        self.browser.get(
            self.live_server_url
            + "/profile/edit/scoreset/{}/".format(scoreset.urn)
        )

        # Check dashboard to see if error message is shown
        messages = self.browser.find_elements_by_class_name("alert-danger")
        self.assertEqual(len(messages), 1)
        self.assertIn(
            "being processed and cannot be edited.", messages[0].text
        )

    def test_publish_limits_edit_fields(self):
        scoreset = data_factories.ScoreSetWithTargetFactory()
        scoreset.add_administrators(self.user)
        scoreset = utilities.publish_dataset(scoreset)

        self.authenticate()
        self.browser.get(
            self.live_server_url
            + "/profile/edit/scoreset/{}/".format(scoreset.urn)
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
            self.browser.find_element_by_id("id_uniprot-offset-identifier")
            self.browser.find_element_by_id("id_refseq-offset-identifier")
            self.browser.find_element_by_id("id_ensembl-offset-identifier")
            self.browser.find_element_by_id("id_uniprot-offset-offset")
            self.browser.find_element_by_id("id_refseq-offset-offset")
            self.browser.find_element_by_id("id_ensembl-offset-offset")

    @mock.patch("core.tasks.send_mail.apply_async")
    @mock.patch("dataset.tasks.publish_scoreset.apply_async")
    def test_publish_updates_states(self, publish_patch, notify_patch):
        scoreset = data_factories.ScoreSetWithTargetFactory()
        scoreset.experiment.add_administrators(self.user)
        scoreset.add_administrators(self.user)
        scoreset.save()

        admin = UserFactory(is_superuser=True)

        # Add some variants
        VariantFactory(scoreset=scoreset)

        self.authenticate()
        self.browser.get(
            self.live_server_url + "/profile/".format(scoreset.urn)
        )

        # Try publishing
        submit = self.browser.find_element_by_id("publish-btn")
        self.perform_action(submit, "click")

        self.browser.switch_to.alert.accept()
        self.browser.get(self.live_server_url + "/profile/")
        icon = self.browser.find_element_by_class_name("processing-icon")
        self.assertIsNotNone(icon)

        # Should be in processing state
        scoreset.refresh_from_db()
        self.assertEqual(scoreset.processing_state, constants.processing)

        # Manually invoke the task
        publish_patch.assert_called()
        tasks.publish_scoreset.apply(**publish_patch.call_args[1])
        self.assertEqual(notify_patch.call_count, 1)

        # Check to see if the publish worked
        scoreset = data_models.scoreset.ScoreSet.objects.first()
        self.assertTrue(scoreset.has_public_urn)
        self.assertTrue(scoreset.parent.has_public_urn)
        self.assertTrue(scoreset.parent.parent.has_public_urn)
        for variant in scoreset.children:
            self.assertTrue(variant.has_public_urn)

        self.browser.get(self.live_server_url + "/profile/")
        icon = self.browser.find_element_by_class_name("success-icon")
        self.assertIsNotNone(icon)

    def test_no_delete_icon_for_public_entry(self):
        scoreset = data_factories.ScoreSetWithTargetFactory()
        scoreset = utilities.publish_dataset(scoreset)
        scoreset.add_administrators(self.user)
        scoreset.experiment.add_administrators(self.user)
        scoreset.experiment.experimentset.add_administrators(self.user)

        icons = self.browser.find_elements_by_class_name("trash-icon")
        self.assertEqual(len(icons), 0)
