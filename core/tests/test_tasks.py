from django.test import TestCase
from django.core import mail

from accounts.factories import UserFactory
from dataset.factories import ScoreSetFactory

from core.tasks import email_admins, email_user, send_to_email


class TestTasks(TestCase):

    def test_send_admin_email_emails_all_admins(self):
        user1 = UserFactory()
        user1.is_superuser = True
        user1.save()

        user2 = UserFactory()
        user2.is_superuser = True
        user2.save()

        obj = ScoreSetFactory()
        email_admins(user1, obj.urn)
        self.assertEqual(len(mail.outbox), 2)

    def test_send_admin_email_can_get_user_by_pk(self):
        user1 = UserFactory()
        user1.is_superuser = True
        user1.save()

        obj = ScoreSetFactory()
        email_admins(user1.pk, obj.urn)
        self.assertEqual(len(mail.outbox), 1)

    def test_send_email(self):
        user1 = UserFactory()
        email_user(
            user1.pk, subject="Hello world",
            message="foo bar", from_email='someone@mail.com')
        self.assertEqual(len(mail.outbox), 1)
        
    def test_send_email_prefers_profile_email(self):
        user1 = UserFactory()
        profile = user1.profile
        profile.email = "hello@net.com"
        profile.save()
        
        email_user(
            user1.pk, subject="Hello world",
            message="foo bar", from_email='someone@mail.com')
        self.assertEqual(mail.outbox[0].to, [user1.profile.email])

    def test_send_email_falls_back_to_user_email(self):
        user1 = UserFactory()
        profile = user1.profile
        profile.email = None
        profile.save()
    
        email_user(
            user1.pk, subject="Hello world",
            message="foo bar", from_email='someone@mail.com')
        self.assertEqual(mail.outbox[0].to, [user1.email])
        
    def test_returns_false_if_no_email(self):
        user1 = UserFactory()
        user1.email = ""
        user1.save()
        
        profile = user1.profile
        profile.email = ""
        profile.save()
    
        email_user(
            user1.pk, subject="Hello world",
            message="foo bar", from_email='someone@mail.com')
        self.assertEqual(len(mail.outbox), 0)
        
    def test_can_send_to_standalone_email(self):
        send_to_email(
            subject="Hello world",
            message="foo bar",
            from_email='from@email.com',
            recipient_list=['to@email.com'],
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_can_no_outbox_if_recipient_list_is_empty(self):
        send_to_email(
            subject="Hello world",
            message="foo bar",
            from_email='from@email.com',
            recipient_list=[],
        )
        self.assertEqual(len(mail.outbox), 0)
