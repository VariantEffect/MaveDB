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
        self.assertNotContains(response, 'id="news-item-')

    def testabout_site_info_displays(self):
        site_info = SiteInformation.objects.create(
            about="This is the about text.",
            citation="This is the citation text."
        )
        response = self.client.get('/')
        self.assertContains(response, site_info.about)

    def testcitation_site_info_displays(self):
        site_info = SiteInformation.objects.create(
            about="This is the about text.",
            citation="This is the citation text."
        )
        response = self.client.get('/')
        self.assertContains(response, site_info.citation)
