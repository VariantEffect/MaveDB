from selenium import webdriver
from selenium.common.exceptions import NoAlertPresentException
from selenium.webdriver.firefox.options import FirefoxBinary, Options

from django.test import LiveServerTestCase
from django.shortcuts import reverse

from accounts.factories import UserFactory

from dataset import factories as data_factories

from .utilities import authenticate_webdriver, LOG_PATH, STAGING_OR_PROD

  
class TestPublishScoreSet(LiveServerTestCase):
    
    def setUp(self):
        self.user = UserFactory()
        if  STAGING_OR_PROD:
            binary = FirefoxBinary('/usr/bin/firefox')
            options = Options()
            options.add_argument('--headless')
        else:
            binary = None
            options = None
        self.browser = webdriver.Firefox(
            log_path=LOG_PATH, firefox_options=options,
            firefox_binary=binary
        )
        if STAGING_OR_PROD:
            self.browser.set_window_position(0, 0)
            self.browser.set_window_size(2560, 1440)
    
    def authenticate(self):
        authenticate_webdriver(
            self.user.username, self.user._password, self, 'browser')
        
    def test_shows_alert_removing_self_as_admin(self):
        second_admin = UserFactory()
        instance = data_factories.ScoreSetFactory()
        instance.add_administrators([self.user, second_admin])
        
        self.authenticate()
        self.browser.get(
            self.live_server_url +
            reverse('accounts:manage_instance', args=(instance.urn,))
        )
        
        # index 1 for editor input, index 1 for search result
        self.browser.find_element_by_id('editors-tab').click()
        self.browser.find_elements_by_class_name(
            'select2-search__field')[1].send_keys(self.user.profile.unique_name)
        self.browser.find_element_by_id(
            'select2-id_editor_management-users-results').click()
        
        self.browser.find_element_by_id('submit-editor-form').click()
        self.browser.switch_to.alert.accept()
        
    def test_no_alert_removing_superuser_removing_self_as_admin(self):
        second_admin = UserFactory()
        instance = data_factories.ScoreSetFactory()
        instance.add_administrators([self.user, second_admin])
        
        self.user.is_superuser = True
        self.user.save()
    
        self.authenticate()
        self.browser.get(
            self.live_server_url +
            reverse('accounts:manage_instance', args=(instance.urn,))
        )
    
        # index 1 for editor input, index 1 for search result
        self.browser.find_element_by_id('editors-tab').click()
        self.browser.find_elements_by_class_name(
            'select2-search__field')[1].send_keys(self.user.profile.unique_name)
        self.browser.find_element_by_id(
            'select2-id_editor_management-users-results').click()
    
        self.browser.find_element_by_id('submit-editor-form').click()
        with self.assertRaises(NoAlertPresentException):
            self.browser.switch_to.alert.accept()
