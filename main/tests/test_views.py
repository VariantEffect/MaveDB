from django.test import TestCase, mock, RequestFactory

from accounts.factories import UserFactory
from core.utilities.tests import TestMessageMixin

from .. import views
from ..factories import SiteInformationFactory, NewsFactory


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
        n1 = NewsFactory()
        n2 = NewsFactory()
        response = self.client.get('/')
        self.assertContains(response, 'id="news-item-1')
        self.assertContains(response, 'id="news-item-2')

    def test_NO_news_items_display(self):
        response = self.client.get('/')
        self.assertEquals(response.context['news_items'].count(), 0)
        self.assertNotContains(response, 'id="news-item-')

    def test_about_site_info_displays(self):
        site_info = SiteInformationFactory()
        response = self.client.get('/')
        self.assertContains(response, site_info.about)

    def test_citation_site_info_displays(self):
        site_info = SiteInformationFactory()
        response = self.client.get('/')
        self.assertContains(response, site_info.citation)
    
    def test_version_hidden_when_empty(self):
        site_info = SiteInformationFactory()
        site_info.version = ''
        site_info.save()
        response = self.client.get('/')
        self.assertNotContains(response, site_info.branch + ':')
        
    def test_version_shown_when_not_empty(self):
        site_info = SiteInformationFactory()
        response = self.client.get('/')
        self.assertContains(
            response, site_info.branch + ': ')
        
        
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
    
    @mock.patch('core.tasks.send_mail.apply_async')
    def test_calls_email_admin_task(self, mock_patch):
        data = self.mock_data()
        admin = UserFactory(is_superuser=True)
        admin.save()
        
        request = self.create_request('post', data=data, path='/contact/')
        response = views.help_contact_view(request)
        mock_patch.assert_called()
        self.assertEqual(
            mock_patch.call_args_list[0][1]['kwargs']['recipient_list'],
            [admin.profile.email]
        )
        
    @mock.patch('core.tasks.send_mail.apply_async')
    def test_calls_send_to_email_reply_task(self, mock_patch):
        data = self.mock_data()
        request = self.create_request('post', data=data, path='/contact/')
        response = views.help_contact_view(request)
        mock_patch.assert_called()