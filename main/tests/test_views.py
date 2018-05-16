from django.test import TestCase, mock, RequestFactory

from accounts.factories import UserFactory
from core.utilities.tests import TestMessageMixin

from .. import views
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
    
    def test_version_hidden_when_empty(self):
        site_info = SiteInformation.objects.create(branch='refactor')
        response = self.client.get('/')
        self.assertNotContains(response, 'refactor:')
        
    def test_version_shown_when_not_empty(self):
        site_info = SiteInformation.objects.create(
            branch='refactor', version='acb1234'
        )
        response = self.client.get('/')
        self.assertContains(response, 'refactor:')
        
        
class TestContactView(TestCase, TestMessageMixin):
    @staticmethod
    def mock_data():
        return {
            'name': "John Smith",
            'email': 'John@smith.com',
            'message': 'This is a test',
            'subject': 'Hello, world!'
        }
    
    def setUp(self):
        self.factory = RequestFactory()
    
    @mock.patch('core.tasks.email_user.delay')
    def test_calls_email_admin_task(self, mock_patch):
        data = self.mock_data()
        admin = UserFactory(is_superuser=True)
        admin.save()
        
        request = self.create_request('post', data=data, path='/contact/')
        response = views.help_contact_view(request)
        mock_patch.assert_called()
        
    @mock.patch('core.tasks.send_to_email.delay')
    def test_calls_send_to_email_reply_task(self, mock_patch):
        data = self.mock_data()
        request = self.create_request('post', data=data, path='/contact/')
        response = views.help_contact_view(request)
        mock_patch.assert_called()