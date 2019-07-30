from django.test import TestCase, mock

from accounts.factories import UserFactory

from ..forms import ContactForm


class TestContactForm(TestCase):
    @staticmethod
    def mock_data():
        return {
            "name": "John Smith",
            "email": "John@smith.com",
            "message": "This is a test",
            "subject": "Hello, world!",
        }

    @mock.patch("core.tasks.send_mail.apply_async")
    def test_emails_admins(self, mock_patch):
        admin = UserFactory(is_superuser=True)
        form = ContactForm(data=self.mock_data())
        form.send_mail()
        mock_patch.assert_called()
        self.assertEqual(
            mock_patch.call_args_list[0][1]["kwargs"]["recipient_list"],
            [admin.profile.email],
        )

    @mock.patch("core.tasks.send_mail.apply_async")
    def test_emails_requester(self, mock_patch):
        form = ContactForm(data=self.mock_data())
        form.send_mail()
        mock_patch.assert_called()
        self.assertEqual(mock_patch.call_count, 1)

    @mock.patch("core.tasks.send_mail.apply_async")
    def test_send_admin_email_if_valid_email_supplied(self, mock_patch):
        data = self.mock_data()
        data["email"] = ""
        form = ContactForm(data=data)
        form.send_mail()
        mock_patch.assert_not_called()
