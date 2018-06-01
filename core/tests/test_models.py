import json
from django.test import TestCase, mock

from .. import models

class TestFailedTaskModel(TestCase):
    
    @mock.patch('core.tasks.send_to_email.delay')
    def test_can_retry_task(self, email_patch):
        kwargs = {
            'subject': 'Test',
            'message': 'Hello world',
            'from_email': 'admin@email.com',
            'recipient_list': ['dudeman@email.com'],
        }
        task = models.FailedTask.objects.create(
            name='send_to_email',
            full_name='core.tasks.send_to_email',
            args=json.dumps([]),
            kwargs=json.dumps(kwargs),
            exception_class=Exception,
            exception_msg='This is an exception',
            traceback=None,
            celery_task_id=1,
            user=None,
        ) # type: models.FailedTask
        
        task.retry_and_delete()
        email_patch.assert_called()
        self.assertEqual(email_patch.call_args[1], kwargs)
        self.assertEqual(models.FailedTask.objects.count(), 0)

    def test_inline_retry_does_not_delete_if_failure(self):
        kwargs = {
            'subject': 'Test',
            'message': 'Hello world',
            'from_email': 'admin@email.com',
            'recipient_list': 1, # should cause a typeerror
        }
        task = models.FailedTask.objects.create(
            name='send_to_email',
            full_name='core.tasks.send_to_email',
            args=json.dumps([]),
            kwargs=json.dumps(kwargs),
            exception_class=Exception,
            exception_msg='This is an exception',
            traceback=None,
            celery_task_id=1,
            user=None,
        )  # type: models.FailedTask
        
        with self.assertRaises(TypeError):
            task.retry_and_delete(inline=True)
            self.assertEqual(models.FailedTask.objects.count(), 1)
            
    def test_can_find_existing_task(self):
        kwargs = {
            'subject': 'Test',
            'message': 'Hello world',
            'from_email': 'admin@email.com',
            'recipient_list': [],
        }
        exc = Exception("Test")
        existing = models.FailedTask.objects.create(
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
        
        task = models.FailedTask(
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
        self.assertEqual(task.find_existing(), existing)
