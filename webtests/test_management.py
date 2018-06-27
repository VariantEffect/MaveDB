from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
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
        
        tab_button = self.browser.find_element_by_id('editors-tab')
        action = ActionChains(self.browser)
        action.move_to_element(tab_button).perform()
        tab_button.click()
        
        search_box = self.browser.find_elements_by_class_name(
            'select2-search__field')[1]
        action = ActionChains(self.browser)
        action.move_to_element(search_box).perform()
        search_box.send_keys(self.user.profile.unique_name)
        
        list_item = self.browser.find_element_by_id(
            'select2-id_editor_management-users-results')
        action = ActionChains(self.browser)
        action.move_to_element(list_item).perform()
        list_item.click()
        
        submit = self.browser.find_element_by_id('submit-editor-form')
        action = ActionChains(self.browser)
        action.move_to_element(submit).perform()
        submit.click()
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
