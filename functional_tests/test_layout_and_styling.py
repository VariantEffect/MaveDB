
"""
Functional testing suite that will test that templates are loading
correctly and css/javascript is functioning as intended from the perspective
of a prospective user.
"""

import time
from .base import FunctionalTest


class LayoutAndStylingTest(FunctionalTest):
    def test_base_template_layout_and_styling(self):
        # Farva opens a new browser, eager to try the new MAVEDB website.
        self.browser.get(self.live_server_url)
        self.browser.set_window_size(1024, 768)

        # The first thing he notices are the lovely navigation bars at the top
        # and bottom of the page.
        header = self.browser.find_element_by_id('navHeader')
        footer = self.browser.find_element_by_id('navFooter')

        # Farva, briefly stuck in a moment of awe caused by the unparalleled
        # beauty of the navigation bar, finally falls back to the realm of
        # reality. He sees links to 'MaveDB', 'Search', 'Upload', 'Help',
        # 'Download', 'Login' and 'Register' pages contained within the
        # navigation header.
        self.assertTrue('MaveDB' in header.text)
        self.assertTrue('Search' in header.text)
        self.assertTrue('Upload' in header.text)
        self.assertTrue('Help' in header.text)
        self.assertTrue('Login' in header.text)
        self.assertTrue('Register' in header.text)
        self.assertTrue('Download' in header.text)

        # Farva loves a good footer. Naturally, he scrolls down to the footer
        # and sees a clean footer bar with two columns: one for the logo on the
        # left and the other for site navigation.
        footer_logo = footer.find_element_by_id("footer-logo")
        self.assertAlmostEqual(
            footer_logo.location['x'] + footer_logo.size['width'],
            512, delta=512*0.05
        )

        footer_links = footer.find_element_by_id("footer-link-container")
        self.assertAlmostEqual(
            footer_links.location['x'] + footer_links.size['width'],
            1024, delta=1024*0.05
        )

    def test_home_page_layout_and_styling(self):
        # Bertha hears about the great database website from Farva during 
        # lunch break on Monday. After a hearty lunch, she decides to check
        # it out for herself. The first thing she notices is the search bar
        # at the top of the page, centered under the navigation bar.
        self.browser.get(self.live_server_url)
        self.browser.set_window_size(1024, 768)
        self.browser.find_element_by_id("keywordSearchForm")
        time.sleep(10)
