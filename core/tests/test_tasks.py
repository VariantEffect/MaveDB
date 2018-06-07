import json

from django.test import TestCase
from django.core import mail
from django.contrib.auth import get_user_model

from accounts.factories import UserFactory
from dataset.factories import ScoreSetFactory

from core import models
from core.tasks import email_admins, send_mail, BaseTask


User = get_user_model()


class TestLogErrorTaskClass(TestCase):
    def test_save_failed_task_updates_existing(self):
        kwargs = {
            'subject': 'Test',
            'message': 'Hello world',
            'from_email': 'admin@email.com',
            'recipient_list': 1, # should cause a typeerror
        }
        exc = Exception("Test")
        task = models.FailedTask.objects.create(
            name='send_to_email',
            full_name='core.tasks.send_to_email',
            args=None,
            kwargs=json.dumps(kwargs),
            exception_class=exc.__class__.__name__,
            exception_msg=str(exc).strip(),
            traceback=None,
            celery_task_id=1,
            user=None,
        ) # type: models.FailedTask
        
        send_mail.on_failure(
            exc=exc,
            task_id=task.id,
            args=[],
            kwargs=kwargs,
            einfo=None,
            user=None
        )
        task.refresh_from_db()
        self.assertEqual(models.FailedTask.objects.count(), 1)
        self.assertEqual(task.failures, 2)
    
    def test_on_failure_saves_task(self):
        kwargs = {
            'subject': 'Test',
            'message': 'Hello world',
            'from_email': 'admin@email.com',
            'recipient_list': 1, # should cause a typeerror
        }
        self.assertEqual(models.FailedTask.objects.count(), 0)
        send_mail.apply(kwargs=kwargs)
        self.assertEqual(models.FailedTask.objects.count(), 1)
        
    def test_get_user_search_by_pk_or_username(self):
        user = UserFactory()
        self.assertIsInstance(BaseTask.get_user(user), User)
        self.assertIsInstance(BaseTask.get_user(user.pk), User)
        self.assertIsInstance(BaseTask.get_user(user.username), User)
        self.assertIsNone(BaseTask.get_user(user.get_full_name()), User)
        

class TestEmailAdminTask(TestCase):
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
        
      
class TestSendToEmailTask(TestCase):
    def test_can_send_to_standalone_email(self):
        send_mail(
            subject="Hello world",
            message="foo bar",
            from_email='from@email.com',
            recipient_list=['to@email.com'],
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_can_no_outbox_if_recipient_list_is_empty(self):
        send_mail(
            subject="Hello world",
            message="foo bar",
            from_email='from@email.com',
            recipient_list=[],
        )
        self.assertEqual(len(mail.outbox), 0)
