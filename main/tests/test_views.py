from django.test import TestCase, mock, RequestFactory

from accounts.factories import UserFactory
from core.utilities.tests import TestMessageMixin
from dataset.factories import ScoreSetWithTargetFactory

from .. import views
from ..factories import SiteInformationFactory, NewsFactory


class TestGetTopN(TestCase):
    def test_top_n(self):
        result = views.get_top_n(3, [1, 1, 2, 3, 4, 5, 3, 3, 3, 2])
        self.assertListEqual(result, [1, 2, 3])


class HomePageTest(TestCase):
    """
    This class tests that the home page is rendered correcly,
    and that site-wide information such as News, About and Citations
    can be created/updated/rendered correctly.
    """

    def test_uses_home_template(self):
        response = self.client.get("/")
        self.assertTemplateUsed(response, "main/home.html")

    def test_render_default_metadata_description_tag(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        tag = (
            '<meta name="description" content="MaveDB - '
            'A repository for MAVE assay datasets.">'
        )
        self.assertContains(response, tag)

    def test_news_items_display(self):
        n1 = NewsFactory()
        n2 = NewsFactory()
        response = self.client.get("/")
        self.assertContains(response, 'id="news-item-1')
        self.assertContains(response, 'id="news-item-2')

    def test_NO_news_items_display(self):
        response = self.client.get("/")
        self.assertEquals(response.context["news_items"].count(), 0)
        self.assertNotContains(response, 'id="news-item-')

    def test_about_site_info_displays(self):
        site_info = SiteInformationFactory()
        response = self.client.get("/")
        self.assertContains(response, site_info.about)

    def test_citation_site_info_displays(self):
        site_info = SiteInformationFactory()
        response = self.client.get("/")
        self.assertContains(response, site_info.citation)

    def test_version_hidden_when_empty(self):
        site_info = SiteInformationFactory()
        site_info.version = ""
        site_info.save()
        response = self.client.get("/")
        self.assertNotContains(response, "Version:")

    def test_version_shown_when_not_empty(self):
        site_info = SiteInformationFactory()
        response = self.client.get("/")
        self.assertContains(response, "Version:")

    def test_private_not_included_in_top_n(self):
        instance = ScoreSetWithTargetFactory()
        response = self.client.get("/")
        self.assertNotContains(response, instance.target.name)

    def test_public_included_in_top_n(self):
        instance = ScoreSetWithTargetFactory()
        instance.private = False
        instance.save()
        response = self.client.get("/")
        self.assertContains(response, instance.target.name)


class TestContactView(TestCase, TestMessageMixin):
    @staticmethod
    def mock_data():
        return {
            "name": "John Smith",
            "email": "John@smith.com",
            "message": "This is a test",
            "subject": "Hello, world!",
        }

    def setUp(self):
        self.factory = RequestFactory()

    @mock.patch("core.tasks.send_mail.apply_async")
    def test_calls_email_admin_task(self, mock_patch):
        data = self.mock_data()
        admin = UserFactory(is_superuser=True)
        admin.save()

        request = self.create_request("post", data=data, path="/contact/")
        response = views.help_contact_view(request)
        mock_patch.assert_called()
        self.assertEqual(
            mock_patch.call_args_list[0][1]["kwargs"]["recipient_list"],
            [admin.profile.email],
        )
        self.assertEqual(response.status_code, 302)

    @mock.patch("core.tasks.send_mail.apply_async")
    def test_calls_send_to_email_reply_task(self, mock_patch):
        data = self.mock_data()
        request = self.create_request("post", data=data, path="/contact/")
        response = views.help_contact_view(request)
        mock_patch.assert_called()
        self.assertEqual(response.status_code, 302)
