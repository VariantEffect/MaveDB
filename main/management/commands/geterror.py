import sys
from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import FailedTask



class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--taskid', type=str, help="Task reference id.",)

    def handle(self, *args, **kwargs):
        taskid = kwargs.get('--taskid', None)
        if taskid:
            taskid = str(taskid)
        else:
            raise ValueError("Task ID required.")

        task = FailedTask.objects.get(celery_task_id=taskid)
        sys.stdout.write('Name: {}\n'.format(task.name))
        sys.stdout.write('Full name: {}\n'.format(task.full_name))
        sys.stdout.write('args: {}\n'.format(task.args))
        sys.stdout.write('kwargs: {}\n'.format(task.kwargs))
        sys.stdout.write('Exception class: {}\n'.format(task.exception_class))
        sys.stdout.write('Exception: {}\n'.format(task.exception_msg))
        sys.stdout.write('Traceback: {}\n'.format(task.traceback))
