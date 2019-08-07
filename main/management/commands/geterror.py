import sys
from django.core.management.base import BaseCommand

from core.models import FailedTask


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--taskid", type=str, default=None, help="Task reference id."
        )
        parser.add_argument(
            "--username", type=str, default=None, help="Submitter's username"
        )

    def handle(self, *args, **kwargs):
        taskid = kwargs.get("taskid", None)
        username = kwargs.get("username", None)
        if taskid:
            taskid = str(taskid)
            tasks = FailedTask.objects.filter(celery_task_id=taskid)
        elif username:
            tasks = FailedTask.objects.filter(user__username=username)
        else:
            raise ValueError("Task ID or Username required.")

        if not tasks.count():
            sys.stdout.write("No tasks found")

        for task in tasks.all():
            sys.stdout.write("{}\n".format("-" * len(task.full_name)))
            sys.stdout.write("Name: {}\n".format(task.name))
            sys.stdout.write("Full name: {}\n".format(task.full_name))
            sys.stdout.write("args: {}\n".format(task.args))
            sys.stdout.write("kwargs: {}\n".format(task.kwargs))
            sys.stdout.write(
                "Exception class: {}\n".format(task.exception_class)
            )
            sys.stdout.write("Exception: {}\n".format(task.exception_msg))
            sys.stdout.write("Traceback: {}\n".format(task.traceback))
            sys.stdout.write("{}\n".format("-" * len(task.full_name)))
