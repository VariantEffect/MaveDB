from selenium import webdriver
from selenium.webdriver.firefox.options import FirefoxBinary, Options

from django.test import LiveServerTestCase, tag
from django.shortcuts import reverse

from mavedb import celery_app

from accounts.factories import UserFactory

from dataset import factories as data_factories

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

    @tag("webtest")
    def test_shows_alert_removing_self_as_admin(self):
        second_admin = UserFactory()
        instance = data_factories.ScoreSetFactory()
        instance.add_administrators([self.user, second_admin])

        self.authenticate()
        self.browser.get(
            self.live_server_url
            + reverse("accounts:manage_instance", args=(instance.urn,))
        )

        # index 0 for admin input, index 1 for search result
        search_box = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[0]
        self.perform_action(
            search_box, "send_keys", self.user.profile.unique_name
        )
        list_item = self.browser.find_element_by_id(
            "select2-id_manage_users-administrators-results"
        )
        self.perform_action(list_item, "click")

        # index 1 for editor input, index 1 for search result
        search_box = self.browser.find_elements_by_class_name(
            "select2-search__field"
        )[1]
        self.perform_action(
            search_box, "send_keys", self.user.profile.unique_name
        )

        list_item = self.browser.find_element_by_id(
            "select2-id_manage_users-editors-results"
        )
        self.perform_action(list_item, "click")

        submit = self.browser.find_element_by_id("submit-user-management-form")
        self.perform_action(submit, "click")

        # Summary step. Click check button with same id below.
        submit = self.browser.find_element_by_id("submit-user-management-form")
        self.perform_action(submit, "click")

        self.browser.switch_to.alert.accept()
