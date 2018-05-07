from django.test import TestCase
from django.core import mail

from accounts.factories import UserFactory
from dataset.factories import ScoreSetFactory

from core.tasks import send_admin_email


class TestTasks(TestCase):

    def test_send_admin_email_emails_all_admins(self):
        user1 = UserFactory()
        user1.is_superuser = True
        user1.save()

        user2 = UserFactory()
        user2.is_superuser = True
        user2.save()

        obj = ScoreSetFactory()
        send_admin_email(user1, obj.urn)
        self.assertEqual(len(mail.outbox), 2)

    def test_send_admin_email_can_get_user_by_pk(self):
        user1 = UserFactory()
        user1.is_superuser = True
        user1.save()

        obj = ScoreSetFactory()
        send_admin_email(user1.pk, obj.urn)
        self.assertEqual(len(mail.outbox), 1)
