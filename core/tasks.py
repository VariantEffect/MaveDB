import traceback
import logging
import time

from kombu.exceptions import (
    OperationalError,
    ConnectionLimitExceeded,
    ConnectionError,
    LimitExceeded,
    KombuError,
    ContentDisallowed,
    SerializationError,
    DecodeError,
    EncodeError,
)

from celery.utils.log import get_task_logger
from celery.task import Task

from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.mail import send_mail as django_send_mail

from mavedb import celery_app

from .models import FailedTask


User = get_user_model()
logger = get_task_logger("core.tasks")
django_logger = logging.getLogger("django")
error_message = (
    "Submitting task {name} raised a {exc_name} error. "
    "Failed task has been saved."
)
network_message = (
    "We are experiencing network issues at the moment. "
    "It may take longer than usual for your submission to be "
    "processed. Contact support if your submission has not "
    "been processed within the week."
)
kombu_errors = (
    OperationalError,
    ConnectionLimitExceeded,
    ConnectionError,
    LimitExceeded,
    KombuError,
    ContentDisallowed,
    SerializationError,
    DecodeError,
    EncodeError,
)


class BaseTask(Task):
    """
    Base task that will save the task to the database and log the error.
    """

    def run(self, *args, **kwargs):
        raise NotImplementedError()

    def apply_async(
        self,
        args=None,
        kwargs=None,
        task_id=None,
        producer=None,
        link=None,
        link_error=None,
        shadow=None,
        **options,
    ):
        django_logger.info(f"Applying async celery function '{self.name}'")
        return super().apply_async(
            args=args,
            kwargs=kwargs,
            task_id=task_id,
            producer=producer,
            link=link,
            link_error=link_error,
            shadow=shadow,
            **options,
        )

    def delay(self, *args, **kwargs):
        if hasattr(self, "name"):
            django_logger.info(
                f"Applying delayed celery function '{self.name}'"
            )
        else:
            django_logger.info(f"Applying delayed celery function '{self}'")
        return super().delay(*args, **kwargs)

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
        # The kwargs can be potentially big in dataset tasks so truncate
        # the variants key before logging.
        str_kwargs = kwargs.copy()
        variants = str(str_kwargs.get("variants", {}))[0:250]
        if variants in str_kwargs:
            str_kwargs["variants"] = variants
        logger.exception(
            "{0} with id {1} called with args={2}, kwargs={3} "
            "raised:\n'{4}' with traceback:\n{5}".format(
                self.name, task_id, args, str_kwargs, exc, einfo
            )
        )
        self.save_failed_task(exc, task_id, args, kwargs, einfo, user)
        super(BaseTask, self).on_failure(exc, task_id, args, kwargs, einfo)

    def save_failed_task(
        self, exc, task_id, args, kwargs, traceback, user=None
    ):
        """
        Save a failed task. If it exists, the modification_date and failure
        counter are updated.
        """
        task, _ = FailedTask.update_or_create(
            name=self.name.split(".")[-1],
            full_name=self.name,
            exc=exc,
            task_id=task_id,
            args=args,
            kwargs=kwargs,
            traceback=str(traceback).strip(),  # einfo
            user=user,
        )
        return task

    def submit_task(
        self,
        args=None,
        kwargs=None,
        async_options=None,
        request=None,
        countdown=10,
    ):
        """
        Calls `task.apply_async` and handles any connection errors by
        logging the error to the `django` default log and saving the
        failed task. If a request object is passed in a warning message will be
        shown to the user using the `messages` contrib module and the task
        will be initialised with the authenticated user as a foreign key.

        Parameters
        ----------
        args : tuple, optional, Default: None
            Un-named task arguments.
        kwargs : dict, optional. Default: None
            Task keyword arguments.
        async_options : dict, optional, Default: None
            Additional kwargs that `apply_async` accepts.
        request : Request, optional. Default: None
            Request object from the view calling this function.
        countdown : int
            Delay before executing celery task.

        Returns
        -------
        tuple[bool, Union[FailedTask, Any]]
            Boolean indicating success or failure, FailedTask or task result.
        """
        if not async_options:
            async_options = {}
        try:
            return (
                True,
                self.apply_async(
                    args=args,
                    kwargs=kwargs,
                    countdown=countdown,
                    **async_options,
                ),
            )
        except kombu_errors as e:
            logger.exception(
                error_message.format(
                    name=self.name, exc_name=e.__class__.__name__
                )
            )
            if request:
                messages.warning(request, network_message)
            task, _ = FailedTask.update_or_create(
                name=self.name.split(".")[-1],
                full_name=self.name,
                exc=e,
                task_id="-1",
                args=args,
                kwargs=kwargs,
                traceback=traceback.format_exc(),
                user=None if not request else request.user,
            )
            return False, task


@celery_app.task(ignore_result=True, base=BaseTask)
def send_mail(subject, message, from_email, recipient_list, **kwargs):
    """Sends a message to all emails in the recipient list."""
    django_send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=recipient_list,
        **kwargs,
    )


@celery_app.task(ignore_result=False, base=BaseTask)
def health_check(a, b, raise_=False, wait=False, allow_prod_db=True):
    """Debug test task."""
    # Specifically requested task failure
    if raise_:
        raise ValueError("Requested test error")

    try:
        from django.db import connection

        db_name = connection.get_connection_params()["database"]
        message = f"'{db_name}' is not the test database"
        if not db_name.startswith("test_") and not allow_prod_db:
            raise ValueError(message)
        if not db_name.startswith("test_") and allow_prod_db:
            logger.info(message)

        if wait:
            time.sleep(wait)

        return a + b

    except Exception as error:
        # Catch any exception to make sure failed task is not saved to
        # prod database.
        logger.exception(error)
        return None
