import json
import io
import pandas as pd
import datetime
import importlib

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

from .utilities import format_delta


User = get_user_model()


def dump_df(df, orient="records"):
    handle = io.StringIO()
    df.to_json(handle, orient=orient)
    handle.seek(0)
    return handle.read()


class TimeStampedModel(models.Model):
    """
    Base model representing a time stamped model updating the modification
    date everytime a change is saved.
    """

    class Meta:
        abstract = True
        ordering = ["-creation_date"]

    creation_date = models.DateField(
        default=datetime.date.today, verbose_name="Creation date"
    )
    modification_date = models.DateField(
        default=datetime.date.today, verbose_name="Modification date"
    )

    def save(self, *args, **kwargs):
        self.modification_date = datetime.date.today()
        return super().save(*args, **kwargs)

    def format_last_edit_date(self):
        return format_delta(self.modification_date)


class FailedTask(models.Model):
    """
    Database model to store a failed task. Adapted from gist
    https://gist.github.com/darklow/c70a8d1147f05be877c3
    """

    creation_date = models.DateTimeField(auto_now_add=True)
    modification_date = models.DateTimeField(null=True, blank=True)
    failures = models.PositiveSmallIntegerField(default=1)

    # Required by instantiate method
    name = models.CharField(max_length=125)
    full_name = models.TextField()
    args = models.TextField(null=True, blank=True)
    kwargs = models.TextField(null=True, blank=True)
    exception_class = models.TextField()
    exception_msg = models.TextField()
    traceback = models.TextField(null=True, blank=True)
    celery_task_id = models.CharField(max_length=36)
    user = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        related_name="failed_tasks",
        null=True,
    )

    class Meta:
        ordering = ("-modification_date",)

    def save(self, *args, **kwargs):
        self.modification_date = timezone.now()
        return super().save(*args, **kwargs)

    def __str__(self):
        return "{0} {1} {2}, [{3}], failures:{4}".format(
            self.name,
            self.args,
            self.kwargs,
            self.exception_class,
            self.failures,
        )

    @classmethod
    def update_or_create(
        cls,
        name,
        full_name,
        exc,
        task_id,
        args,
        kwargs,
        traceback=None,
        user=None,
    ):
        """
        Save a failed task. If it exists, the modification_date and failure
        counter are updated.
        """
        # Find if task with same args, name and exception already exists
        # If it does, update failures count and last updated_at
        task = cls.instantiate_task(
            name=name,
            full_name=full_name,
            exc=exc,
            task_id=task_id,
            args=args,
            kwargs=kwargs,
            traceback=traceback,
            user=user,
        )
        existing_task = task.find_existing()
        if existing_task is not None:
            existing_task.failures += 1
            existing_task.save(force_update=True, update_fields=("failures",))
            task = existing_task
            created = False
        else:
            task.save(force_insert=True)
            created = True
        return task, created

    @classmethod
    def instantiate_task(
        cls,
        name,
        full_name,
        exc,
        task_id,
        args,
        kwargs,
        traceback=None,
        user=None,
    ):
        """
        Convenience function to instantiate a task, handling the `json.dumps`
        process of args and kwargs and the extraction of exception traceback,
        message and class.

        Parameters
        ----------
        name : str
            Task function name
        full_name : str
            Task full import name with format `module.tasks.function_name`
        exc : Exception
            The exception raised at runtime.
        task_id : str
            Character task id given by celery.
        args : tuple
            Task arguments
        kwargs : dict
            Task kwargs
        traceback : ~billiard.einfo.ExceptionInfo`, optional.
            Traceback object
        user : User, optional.
            The user from the request that triggered the task submission.

        Returns
        -------
        FailedTask
        """
        task = cls(
            celery_task_id=task_id,
            full_name=full_name,
            name=name,
            exception_class=exc.__class__.__name__,
            exception_msg=str(exc).strip(),
            traceback=str(traceback).strip(),
            user=user,
        )

        if args:
            args = [
                dump_df(i) if isinstance(i, pd.DataFrame) else i for i in args
            ]
            task.args = json.dumps(list(args))
        if kwargs:
            import io

            for key, item in kwargs.items():
                if isinstance(item, pd.DataFrame):
                    kwargs[key] = dump_df(item)
            task.kwargs = json.dumps(kwargs, sort_keys=True)
        return task

    def find_existing(self):
        """
        Finds the first matching task according to `args`, `kwargs`,
        `exception_class` and `exception_msg`
        """
        existing_tasks = FailedTask.objects.filter(
            args=self.args,
            full_name=self.full_name,
            exception_class=self.exception_class,
            exception_msg=self.exception_msg,
        )
        # Do a dictionary comparison instead since dict
        # keys might not have a deterministic ordering.
        # Breaks on first match.
        existing_task = None
        for task in existing_tasks.all():
            task_kwargs = None
            self_kwargs = None

            if task.kwargs:
                task_kwargs = json.loads(task.kwargs)
            if self.kwargs:
                self_kwargs = json.loads(self.kwargs)

            if task_kwargs == self_kwargs:
                existing_task = task
                break

        return existing_task

    def retry(self, inline=False):
        """
        Re-loads the task parameters and tries again. Executes task
        synchronously when inline is `False`.
        
        Parameters
        ----------
        inline : `bool`
            Execute task without celery.

        Returns
        -------
        `any`
            Task result
        """
        mod_name, func_name = self.full_name.rsplit(".", 1)
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name)

        args = json.loads(self.args) if self.args else ()
        kwargs = json.loads(self.kwargs) if self.kwargs else {}

        if inline:
            return func(*args, **kwargs)
        else:
            return func.submit_task(args=args, kwargs=kwargs)

    def retry_and_delete(self, inline=False):
        """
        Retry a task and delete it upon submission.
        Setting `inline` to true will call the task synchronously without
        celery in a try/except block and only delete on success. A new task
        will be created on additional failures when `inline` is False.
        
        Parameters
        ----------
        inline : `bool`
            Execute task without celery.

        Returns
        -------
        `any`
            Task result
        """
        if inline:
            try:
                result = self.retry(inline=inline)
                self.delete()
                return result
            except Exception as e:
                raise e
        else:
            self.delete()
            return self.retry(inline=inline)
