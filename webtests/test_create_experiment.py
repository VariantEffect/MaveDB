from django.test import LiveServerTestCase

from selenium.webdriver.firefox.webdriver import WebDriver

from .utilities import authenticate_webdriver


class CreateExperimentLiveTest(LiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        cls.selenium = WebDriver()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_failed_submission_with_repopulate_keywords(self):
        authenticate_webdriver('userman', 'supersecret', self)
        self.selenium.get(self.live_server_url + '/experiment/new/')

        keyword_field = self.selenium.find_element_by_id("id_keywords")
        all_options = keyword_field.find_elements_by_tag_name("option")
        for option in all_options:
            print("Value is: %s" % option.get_attribute("value"))
            option.click()



