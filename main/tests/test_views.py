
"""
Testing suite for main app views
"""

from django.test import TestCase

from ..models import News, SiteInformation


class HomePageTest(TestCase):
    """
    This class tests that the home page is rendered correcly,
    and that site-wide information such as News, About and Citations
    can be created/updated/rendered correctly.
    """
    def test_uses_home_template(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'main/home.html')

    def test_news_items_display(self):
        News.objects.create(text="Hello World!")
        News.objects.create(text="Greetings Space Ranger!")

        response = self.client.get('/')
        self.assertEquals(response.context['news_items'].count(), 2)

    def test_NO_news_items_display(self):
        response = self.client.get('/')
        self.assertEquals(response.context['news_items'].count(), 0)
        self.assertContains(response, "No announcements at this time.")

    def test_about_site_info_displays(self):
        site_info = SiteInformation.objects.create(
            about="This is the about text.",
            citation="This is the citation text."
        )
        response = self.client.get('/')
        self.assertContains(response, site_info.about)

    def test_citation_site_info_displays(self):
        site_info = SiteInformation.objects.create(
            about="This is the about text.",
            citation="This is the citation text."
        )
        response = self.client.get('/')
        self.assertContains(response, site_info.citation)

    def test_NO_site_info_displays(self):
        response = self.client.get('/')
        self.assertNotContains(response, 'id="citation"')
        self.assertNotContains(response, 'id="about"')


class SearchPageTest(TestCase):
    """
    This class tests that the search page is rendered correcly.
    """
    def setUp(self):
        TestCase.setUp(self)

    def test_uses_search_template(self):
        response = self.client.get('/search/')
        self.assertTemplateUsed(response, 'main/search.html')

    def test_table_renders_sorted_by_date_upon_page_load(self):
        self.fail("Write this test!")
