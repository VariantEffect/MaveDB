
"""
Functional testing suite that will test that templates are loading
correctly and css/javascript is functioning as intended from the perspective
of a prospective user.
"""

import time
import datetime
from .base import FunctionalTest

from main.models import News, SiteInformation


class LayoutAndStylingTest(FunctionalTest):

    def setUp(self):
        self.site_info = SiteInformation.objects.create(
            about="This is the about text.",
            citation="This is the citation text."
        )
        FunctionalTest.setUp(self)
    
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
        self.assertLessEqual(
            footer_logo.location['x'] - footer_logo.size['width'], 512)

        footer_links = footer.find_element_by_id("footer-link-container")
        self.assertGreaterEqual(
            footer_links.location['x'] + footer_links.size['width'], 512)

    def test_home_page_layout_and_styling(self):
        # Bertha hears about the great database website from Farva during
        # lunch break on Monday. After a hearty lunch, she decides to check
        # it out for herself. The first thing she notices is the search bar
        # at the top of the page, centered under the navigation bar.
        self.browser.get(self.live_server_url)
        self.browser.set_window_size(1024, 768)
        self.browser.find_element_by_id("keywordSearchForm")

        # Conincidentally, while Bertha visits the site, the site admin
        # concurrently posts two new announcements.
        news_item_1 = News.objects.create(text="Hello World!")
        news_item_2 = News.objects.create(text="Hello Bertha!")

        # On the left side of the screen Bertha sees the two announcements.
        self.browser.refresh()
        result_item_1 = self.browser.find_element_by_id("news-item-1")
        result_item_2 = self.browser.find_element_by_id("news-item-2")

        self.assertIn(news_item_1.message, result_item_1.text)
        self.assertIn(news_item_2.message, result_item_2.text)

        # The system admin made a mistake with some of the item dates and
        # Decides to reverse their order.
        news_item_1.date -= datetime.timedelta(days=5)
        news_item_1.save()

        # Bertha decides to refresh the page for story convenience reasons.
        # Good Bertha.
        self.browser.refresh()
        result_item_1 = self.browser.find_element_by_id("news-item-1")
        result_item_2 = self.browser.find_element_by_id("news-item-2")

        self.assertIn(news_item_2.message, result_item_1.text)
        self.assertIn(news_item_1.message, result_item_2.text)

        # Bertha begins to wonder why she's even here in the first place.
        # She decides to read the "About" text.
        about = self.browser.find_element_by_id("about")
        self.assertIn(self.site_info.about, about.text)

        # Content with the service provided, Bertha wonders how to cite
        # MaveDB in her publications. She looks towards the 'Citation' section.
        citation = self.browser.find_element_by_id("citation")
        self.assertIn(self.site_info.citation, citation.text)

