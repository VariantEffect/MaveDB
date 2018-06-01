from django.test import TestCase, mock

from accounts.factories import UserFactory

from ..forms import ContactForm


class TestContactForm(TestCase):
    @staticmethod
    def mock_data():
        return {
            'name': "John Smith",
            'email': 'John@smith.com',
            'message': 'This is a test',
            'subject': 'Hello, world!'
        }
    
    @mock.patch('accounts.tasks.email_user.delay')
    def test_emails_admins(self, mock_patch):
        UserFactory(is_superuser=True)
        form = ContactForm(data=self.mock_data())
        form.send_mail()
        mock_patch.assert_called()
        
    @mock.patch('core.tasks.send_to_email.delay')
    def test_emails_requester(self, mock_patch):
        UserFactory(is_superuser=True)
        UserFactory(is_superuser=True)
        
        form = ContactForm(data=self.mock_data())
        form.send_mail()
        mock_patch.assert_called()
        self.assertEqual(mock_patch.call_count, 1)
        
    @mock.patch('accounts.tasks.email_user.delay')
    def test_send_admin_email_if_valid_email_supplied(self, mock_patch):
        data = self.mock_data()
        data['email'] = ""
        form = ContactForm(data=data)
        form.send_mail()
        mock_patch.assert_not_called()
