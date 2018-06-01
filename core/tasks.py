import json

from celery.utils.log import get_task_logger
from celery.task import Task

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.urls import reverse
from django.core.mail import send_mail

from urn.models import get_model_by_urn
from dataset import models
from mavedb import celery_app

from .models import FailedTask


User = get_user_model()
logger = get_task_logger(__name__)


class LogErrorsTask(Task):
    """
    Base task that will save the task to the database and log the error.
    """
    @staticmethod
    def get_user(user):
        if isinstance(user, User):
            return user

        if isinstance(user, int):
            if User.objects.filter(pk=user).count():
                user = User.objects.get(pk=user)
            else:
                user = None
        elif isinstance(user, str):
            if User.objects.filter(username=user).count():
                user = User.objects.get(username=user)
            else:
                user = None
        else:
            user = None

        return user
        
    def on_failure(self, exc, task_id, args, kwargs, einfo, user=None):
        """
        Error handler.

        This is run by the worker when the task fails.

        Parameters:
        ----------
        exc : `Exception`
            The exception raised by the task.
        task_id : `str`
            Unique id of the failed task.
        args : `Tuple`
            Original arguments for the task that failed.
        kwargs : `Dict`
            Original keyword arguments for the task that failed.
        einfo : `~billiard.einfo.ExceptionInfo`
            Exception information.
        user : `User`, `int` or `str`.
            User that called the task. Applicable to `publish_scoreset`
            and `create_variants` tasks. Will search User model if user
            is an int pk or str username.

        Returns
        -------
        `None`
            The return value of this handler is ignored.
        """
        user = self.get_user(user)
        logger.exception("{0} with id {1} called with args={2}, kwargs={3} "
                         "raised:\n\n{4}\n\nInfo:\n\n{5}".format(
            self.name, task_id, args, kwargs, exc, einfo
        ))
        self.save_failed_task(exc, task_id, args, kwargs, einfo, user)
        super(LogErrorsTask, self).on_failure(exc, task_id, args, kwargs, einfo)
    
    def save_failed_task(self, exc, task_id, args, kwargs, traceback, user=None):
        """
        Save a failed task. If it exists, the modification_date and failure
        counter are updated.
        """
        task = FailedTask(
            celery_task_id=task_id,
            full_name=self.name,
            name=self.name.split('.')[-1],
            exception_class=exc.__class__.__name__,
            exception_msg=str(exc).strip(),
            traceback=str(traceback).strip(), # einfo
            user=user,
        )
        if args:
            task.args = json.dumps(list(args))
        if kwargs:
            task.kwargs = json.dumps(kwargs, sort_keys=True)
        
        # Find if task with same args, name and exception already exists
        # If it does, update failures count and last updated_at
        existing_task = task.find_existing()
        if existing_task is not None:
            existing_task.failures += 1
            existing_task.save(force_update=True, update_fields=('failures',))
        else:
            task.save(force_insert=True)


@celery_app.task(ignore_result=True, base=LogErrorsTask)
def send_to_email(subject, message, from_email, recipient_list, **kwargs):
    """Sends a message to all emails in the recipient list."""
    if recipient_list:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            **kwargs
        )


@celery_app.task(ignore_result=True, base=LogErrorsTask)
def email_admins(user, urn, base_url=""):
    """
    Sends an email to all admins.

    Parameters
    ----------
    user : `auth.User`
        The user who published the instance.
    urn : `str`
        URN of the instance created.
    base_url : `str`
        Host domain name
    """
    if isinstance(user, int):
        user = User.objects.get(pk=user)
    instance = get_model_by_urn(urn)
    
    url = base_url
    if isinstance(instance, models.scoreset.ScoreSet):
        url += reverse('dataset:scoreset_detail', args=(instance.urn,))
    elif isinstance(instance, models.experiment.Experiment):
        url += reverse('dataset:experiment_detail', args=(instance.urn,))
    elif isinstance(instance, models.experimentset.ExperimentSet):
        url += reverse('dataset:experimentset_detail', args=(instance.urn,))
    else:
        return
    
    template_name = "core/alert_admin_new_entry_email.html"
    admins = User.objects.filter(is_superuser=True)
    message = render_to_string(template_name, {
        'user': user,
        'url': url,
        'class_name': type(instance).__name__,
    })
    
    subject = "[MAVEDB ADMIN] New entry requires your attention."
    for admin in admins:
        logger.info("Sending email to {}".format(admin.username))
        admin.email_user(subject, message)
