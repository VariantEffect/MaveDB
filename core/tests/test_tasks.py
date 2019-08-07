from kombu.exceptions import KombuError

from django.test import TestCase, RequestFactory, mock
from django.contrib import messages
from django.core import mail
from django.contrib.auth import get_user_model

from accounts.factories import UserFactory

from core import models
from core.utilities.tests import TestMessageMixin
from core.tasks import send_mail, BaseTask


User = get_user_model()


def raise_error(*args, **kwargs):
    raise KombuError("Could not queue task.")


class TestBaseTask(TestCase, TestMessageMixin):
    def setUp(self):
        self.factory = RequestFactory()

    def test_save_failed_task_updates_existing(self):
        kwargs = {
            "subject": "Test",
            "message": "Hello world",
            "from_email": "admin@email.com",
            "recipient_list": 1,  # should cause a typeerror
        }
        exc = Exception("Test")
        task, created = models.FailedTask.update_or_create(
            name="send_mail",
            full_name="core.tasks.send_mail",
            args=None,
            kwargs=kwargs,
            traceback=None,
            task_id=1,
            user=None,
            exc=exc,
        )
        self.assertTrue(created)

        send_mail.on_failure(
            exc=exc,
            task_id=task.celery_task_id,
            args=[],
            kwargs=kwargs,
            einfo=None,
            user=None,
        )
        task.refresh_from_db()
        self.assertEqual(models.FailedTask.objects.count(), 1)
        self.assertEqual(task.failures, 2)

    @mock.patch.object(BaseTask, "apply_async", side_effect=raise_error)
    def test_sends_message_on_queue_fail(self, patch):
        request = self.create_request(method="get", path="/")
        request.user = UserFactory()
        task = BaseTask()
        task.submit_task(request=request)
        self.assertEqual(len(list(messages.get_messages(request))), 1)

    def test_on_failure_saves_task(self):
        kwargs = {
            "subject": "Test",
            "message": "Hello world",
            "from_email": "admin@email.com",
            "recipient_list": 1,  # should cause a typeerror
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


class TestSendMailTask(TestCase):
    def test_can_send_to_standalone_email(self):
        send_mail(
            subject="Hello world",
            message="foo bar",
            from_email="from@email.com",
            recipient_list=["to@email.com"],
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_can_no_outbox_if_recipient_list_is_empty(self):
        send_mail(
            subject="Hello world",
            message="foo bar",
            from_email="from@email.com",
            recipient_list=[],
        )
        self.assertEqual(len(mail.outbox), 0)
