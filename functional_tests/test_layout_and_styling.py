
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
            _about="This is the about text.",
            _citation="This is the citation text."
        )
        FunctionalTest.setUp(self)

    def test_base_template_layout_and_styling(self):
        # Farva opens a new browser, eager to try the new MAVEDB website.
        self.browser.get(self.live_server_url)
        self.browser.set_window_size(1024, 768)

        # The first thing he notices are the lovely navigation bars
        header = self.browser.find_element_by_class_name('header')

        # Farva loves a good footer. Naturally, he scrolls down to the footer
        # and sees a clean footer bar with two columns: one for the logo on the
        # left and the other for site navigation.
        searchbar = header.find_element_by_class_name("navbar-search")
        self.assertGreaterEqual(
            searchbar.location['x'] + searchbar.size['width'], 512)

    def test_home_page_layout_and_styling(self):
        # Bertha hears about the great database website from Farva during
        # lunch break on Monday. After a hearty lunch, she decides to check
        # it out for herself. The first thing she notices is the search bar
        # at the top of the page, centered under the navigation bar.
        self.browser.get(self.live_server_url)
        self.browser.set_window_size(1024, 768)

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
        self.assertIn(self.site_info._about, about.get_attribute('innerHTML'))

        # Content with the service provided, Bertha wonders how to cite
        # MaveDB in her publications. She looks towards the 'Citation' section.
        citation = self.browser.find_element_by_id("citation")
        self.assertIn(
            self.site_info._citation, citation.get_attribute('innerHTML'))
