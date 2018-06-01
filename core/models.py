import json
import datetime
import importlib

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

from .utilities import format_delta


User = get_user_model()


class TimeStampedModel(models.Model):
    """
    Base model representing a time stamped model updating the modification
    date everytime a change is saved.
    """
    class Meta:
        abstract = True
        ordering = ['-creation_date']

    creation_date = models.DateField(
        default=datetime.date.today,
        verbose_name='Creation date',
    )
    modification_date = models.DateField(
        default=datetime.date.today,
        verbose_name='Modification date',
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
    name = models.CharField(max_length=125)
    full_name = models.TextField()
    args = models.TextField(null=True, blank=True)
    kwargs = models.TextField(null=True, blank=True)
    exception_class = models.TextField()
    exception_msg = models.TextField()
    traceback = models.TextField(null=True, blank=True)
    celery_task_id = models.CharField(max_length=36)
    failures = models.PositiveSmallIntegerField(default=1)
    user = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        related_name='failed_tasks',
        null=True,
    )
    
    class Meta:
        ordering = ('-modification_date',)
        
    def save(self, *args, **kwargs):
        self.modification_date = timezone.now()
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return '{0} {1} [{2}]'.format(
            self.name, self.args, self.exception_class)
    
    def find_existing(self):
        existing_tasks = FailedTask.objects.filter(
            args=self.args,
            full_name=self.full_name,
            exception_class=self.exception_class,
            exception_msg=self.exception_msg,
        )
        # Do a dictionary comparison instead since dict
        # keys might not have a deterministic ordering.
        existing_task = None
        for task in existing_tasks.all():
            task_kwargs = None
            self_kwargs = None
            
            if task.kwargs:
                task_kwargs = json.loads(task.kwargs)
            if self.kwargs:
                self_kwargs = json.loads(self.kwargs)
            
            if task_kwargs is None or self_kwargs is None:
                continue
            elif task_kwargs == self_kwargs:
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
        mod_name, func_name = self.full_name.rsplit('.', 1)
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name)

        args = json.loads(self.args) if self.args else ()
        kwargs = json.loads(self.kwargs) if self.kwargs else {}
        
        if inline:
            return func(*args, **kwargs)
        else:
            return func.delay(*args, **kwargs)

    def retry_and_delete(self, inline=False):
        """
        Retry a task and delete it. Setting `inline` to true will call
        the task synchronously without celery in a try/except block and
        only delete on success. A new task will be created on additional
        failures when `inline` is False.
        
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
