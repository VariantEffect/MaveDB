import re
import logging
import datetime
from datetime import timedelta
from typing import Optional, List

from social_django.models import UserSocialAuth

from django.template.loader import render_to_string
from django.contrib.auth.models import User
from django.db import models
from django.db.models import QuerySet
from django.db.models.signals import post_save
from django.contrib.postgres.fields import JSONField
from django.dispatch import receiver
from django.utils.html import format_html
from django.utils.crypto import get_random_string

from core.models import TimeStampedModel
from core.tasks import send_mail

from dataset.models.experimentset import ExperimentSet
from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet

from .permissions import (
    GroupTypes,
    user_is_anonymous,
    instances_for_user_with_group_permission,
)


AUTH_TOKEN = r"[a-zA-Z0-9]{64}"
AUTH_TOKEN_RE = re.compile(AUTH_TOKEN)
logger = logging.getLogger("django")


class Profile(TimeStampedModel):
    """
    A Profile is associated with a user. It contains helper functions
    which can be used to format the users details like orcid url, name, and
    contains utility functions for obtaining :class:`DatasetModel` instances
    that are associated with the user.

    Attributes
    ----------
    user : :class:`models.OnOneToOneField`
        The foreign key relationship associating a profile with a user.
    """

    TOKEN_LENGTH = 64
    TOKEN_EXPIRY = 14

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email = models.EmailField(default=None, blank=True, null=True)
    auth_token = models.CharField(
        max_length=TOKEN_LENGTH, null=True, default=None
    )
    auth_token_expiry = models.DateField(null=True, default=None)
    submission_errors = JSONField(null=True, blank=True, default=None)

    def __str__(self):
        return "{}_profile".format(self.user.username)

    def get_submission_scores_errors(self) -> Optional[List[str]]:
        if self.submission_errors is None:
            return None
        return self.submission_errors.get("score_data", None)

    def get_submission_counts_errors(self) -> Optional[List[str]]:
        if self.submission_errors is None:
            return None
        return self.submission_errors.get("count_data", None)

    def set_submission_scores_errors(
        self, data: Optional[List[str]] = None
    ) -> "Profile":
        if not self.submission_errors:
            self.submission_errors = {}
        self.submission_errors["score_data"] = data
        return self

    def set_submission_counts_errors(
        self, data: Optional[List[str]] = None
    ) -> "Profile":
        if not self.submission_errors:
            self.submission_errors = {}
        self.submission_errors["count_data"] = data
        return self

    def clear_submission_errors(self) -> "Profile":
        self.submission_errors = {}
        return self

    def generate_token(self):
        self.auth_token = get_random_string(length=self.TOKEN_LENGTH)
        self.auth_token_expiry = datetime.date.today() + timedelta(
            days=self.TOKEN_EXPIRY
        )
        self.save()
        return self.auth_token, self.auth_token_expiry

    def auth_token_is_valid(self, token=None):
        if token is None:
            token = self.auth_token
        return (
            self.auth_token == token
            and datetime.date.today() < self.auth_token_expiry
        )

    def email_user(self, subject, message, from_email=None, **kwargs):
        email = self.email or self.user.email
        if email:
            task_kwargs = dict(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[email],
            )
            task_kwargs.update(**kwargs)
            send_mail.submit_task(kwargs=task_kwargs)
        else:
            logger.warning(
                "Tried email user {} from Profile but could not find an "
                "email address.".format(self.user.username)
            )

    def notify_user_submission_status(
        self, success, task_id=None, description=None
    ):
        subject = "Your submission has been processed."
        template_name = "accounts/celery_job_status_email.html"
        message = render_to_string(
            template_name,
            {
                "profile": self,
                "success": success,
                "task_id": task_id,
                "description": description,
            },
        )
        self.email_user(subject=subject, message=message)

    def notify_user_group_change(self, instance, action, group):
        if action == "removed":
            conjunction = "from"
        else:
            conjunction = "for"

        if group in ("administrator", "editor"):
            group = "an {}".format(group)
        else:
            group = "a {}".format(group)

        template_name = "accounts/group_change_email.html"
        subject = "Updates to entry {}.".format(instance.urn)
        message = render_to_string(
            template_name,
            {
                "profile": self,
                "group": group,
                "conjunction": conjunction,
                "url": instance.get_url(),
                "action": action,
                "urn": instance.urn,
            },
        )
        self.email_user(subject=subject, message=message)

    @classmethod
    def non_anonymous_profiles(cls):
        """Returns a list of all non-anonymous profiles."""
        return [p for p in cls.objects.all() if not p.is_anon()]

    @property
    def unique_name(self):
        return "{} | {}".format(self.get_display_name(), self.user.username)

    def is_anon(self):
        """
        Checks if the user associated with this profile is anonymous.

        Returns
        -------
        `bool`
            True if the profile and user are anonymous.
        """
        return user_is_anonymous(self.user)

    def get_orcid_url(self):
        """
        Returns the ORCID url for the owner of this profile, which is
        based off the username parsed from the ORCID OAuth.

        Returns
        -------
        `str` or `None`
            The ORCID url for this user, otherwise None if the user is
            anonymous.
        """
        if self.is_anon():
            return None
        else:
            return "https://orcid.org/{}".format(self.user.username)

    def get_display_name_hyperlink(self):
        """
        Returns the credit-name formatted as a hyperlink tag referencing the
        ORCID url otherwise full name if it cannot be found.

        Returns
        -------
        `str`
            Returns 'anonymous user' if the user is anon, otherwise a
            <a/> tag with the user's full name as the inner HTML.

        Returns
        -------
        `str`
            Returns 'anonymous user' if the user is anon, otherwise a
            <a/> tag with the user's credit-name as the inner HTML.
        """
        if self.is_anon():
            return "anonymous user"
        else:
            return format_html(
                '<a target="_blank" href="{url}">{name}</a>'.format(
                    url=self.get_orcid_url(), name=self.get_display_name()
                )
            )

    def get_full_name_hyperlink(self):
        """
        Returns the full name formatted as a hyperlink tag referencing the
        ORCID url.

        Returns
        -------
        `str`
            Returns 'anonymous user' if the user is anon, otherwise a
            <a/> tag with the user's full name as the inner HTML.
        """
        if self.is_anon():
            return "anonymous user"
        else:
            return format_html(
                '<a target="_blank" href="{url}">{name}</a>'.format(
                    url=self.get_orcid_url(), name=self.get_full_name()
                )
            )

    def get_display_name(self):
        """
        Returns the users credit name if one exists for this user, otherwise
        calls :func:`get_full_name`.

        Returns
        -------
        `str`
            Credit-name, the result of :func:`get_full_name` or None if the user
            is anon.
        """
        if self.is_anon():
            return None

        social_auth = UserSocialAuth.get_social_auth_for_user(
            self.user
        ).first()
        if not isinstance(social_auth, UserSocialAuth):
            return self.get_full_name()
        else:
            credit_name = social_auth.extra_data.get("credit-name", None)
            if not credit_name:
                return self.get_full_name()
            return credit_name

    def get_full_name(self):
        """
        Returns the users full name formatted as "<first>, <last>" If the user
        does not have a last name, the first name is returned. If the user has
        neither, then the username is returned.

        Returns
        -------
        `str`
            Full, first or username as a string. Returns None if the user is
            anon.
        """
        if self.is_anon():
            return None
        if not self.user.last_name:
            if not self.user.first_name:
                return self.user.username
            else:
                # support for mononyms
                return self.user.first_name.capitalize()
        else:
            return "{} {}".format(
                self.user.first_name.capitalize(),
                self.user.last_name.capitalize(),
            )

    def get_short_name(self):
        """
        Returns the users short name formatted as
        "<last name>, <first name initial>". If the user does not have a last
        name, the first name is returned. If the user has
        neither, then the username is returned.

        Returns
        -------
        `str`
            Short name, first or username as a string. Returns None if the user
            is anon.
        """
        if self.is_anon():
            return None
        if not self.user.last_name:
            if not self.user.first_name:
                return self.user.username
            else:
                # support for mononyms
                return self.user.first_name.capitalize()
        else:
            return "{}, {}".format(
                self.user.last_name.capitalize(),
                self.user.first_name[0].capitalize(),
            )

    # Contributor
    # ----------------------------------------------------------------------- #
    def contributor_instances(
        self,
        experimentset_queryset=None,
        experiment_queryset=None,
        scoreset_queryset=None,
    ):
        """
        Return a list of :class:`DatasetModel` instances the user is a
        contributor for (view, edit, or admin).

        Returns
        -------
        `list`
        """
        instances = (
            list(self.contributor_experimentsets(experimentset_queryset))
            + list(self.contributor_experiments(experiment_queryset))
            + list(self.contributor_scoresets(scoreset_queryset))
        )
        return instances

    def contributor_experimentsets(self, queryset=None):
        """
        Return a list of :class:`ExperimentSet` instances the user
        contributes to.

        Returns
        -------
        `QuerySet`
        """
        if queryset is None:
            queryset = ExperimentSet.objects.all()

        return instances_for_user_with_group_permission(
            user=self.user, queryset=queryset, group_type="any"
        ).order_by("urn")

    def contributor_experiments(self, queryset=None):
        """
        Return a list of :class:`Experiment` instances the user
        contributes to.

        Returns
        -------
        `QuerySet`
        """
        if queryset is None:
            queryset = Experiment.objects.all()

        return instances_for_user_with_group_permission(
            user=self.user, queryset=queryset, group_type="any"
        ).order_by("urn")

    def contributor_scoresets(self, queryset=None):
        """
        Return a list of :class:`ScoreSet` instances the user
        contributes to.

        Returns
        -------
        `QuerySet`
        """
        if queryset is None:
            queryset = ScoreSet.objects.all()

        return instances_for_user_with_group_permission(
            user=self.user, queryset=queryset, group_type="any"
        ).order_by("urn")

    def public_contributor_experimentsets(self, queryset=None):
        """Filters out private experimentsets"""
        instances = self.contributor_experimentsets(queryset).exclude(
            private=True
        )
        return instances.order_by("urn")

    def public_contributor_experiments(self, queryset=None):
        """Filters out private experiments"""
        instances = self.contributor_experiments(queryset).exclude(
            private=True
        )
        return instances.order_by("urn")

    def public_contributor_scoresets(self, queryset=None):
        """Filters out private scoresets"""
        instances = self.contributor_scoresets(queryset).exclude(private=True)
        return instances.order_by("urn")

    # Administrator
    # ----------------------------------------------------------------------- #
    def administrator_instances(self, queryset=None):
        """
        Return a list of :class:`DatasetModel` instances the user is an admin
        for.

        Returns
        -------
        `list`
        """
        instances = (
            list(self.administrator_experimentsets(queryset))
            + list(self.administrator_experiments(queryset))
            + list(self.administrator_scoresets(queryset))
        )
        return instances

    def administrator_experimentsets(self, queryset=None):
        """
        Return a list of :class:`ExperimentSet` instances the user
        administrates.

        Returns
        -------
        `QuerySet`
        """
        if queryset is None:
            queryset = ExperimentSet.objects.all()
        return instances_for_user_with_group_permission(
            user=self.user, queryset=queryset, group_type=GroupTypes.ADMIN
        )

    def administrator_experiments(self, queryset=None):
        """
        Return a list of :class:`Experiment` instances the user
        administrates.

        Returns
        -------
        `QuerySet`
        """
        if queryset is None:
            queryset = Experiment.objects.all()
        return instances_for_user_with_group_permission(
            user=self.user, queryset=queryset, group_type=GroupTypes.ADMIN
        )

    def administrator_scoresets(self, queryset=None):
        """
        Return a list of :class:`Experiment` instances the user
        administrates.

        Returns
        -------
        `QuerySet`
        """
        if queryset is None:
            queryset = ScoreSet.objects.all()
        return instances_for_user_with_group_permission(
            user=self.user, queryset=queryset, group_type=GroupTypes.ADMIN
        )

    # Editor
    # ---------------------------------------------------------------------- #
    def editor_instances(self, queryset=None):
        """
        Return a list of :class:`DatasetModel` instances the user is a viewer
        for.

        Returns
        -------
        `QuerySet`
        """
        instances = (
            list(self.editor_experimentsets(queryset))
            + list(self.editor_experiments(queryset))
            + list(self.editor_scoresets(queryset))
        )
        return instances

    def editor_experimentsets(self, queryset=None):
        """
        Return a list of :class:`ExperimentSet` instances the user
        can only view.

        Returns
        -------
        `QuerySet`
        """
        if queryset is None:
            queryset = ExperimentSet.objects.all()
        return instances_for_user_with_group_permission(
            user=self.user, queryset=queryset, group_type=GroupTypes.EDITOR
        )

    def editor_experiments(self, queryset=None):
        """
        Return a list of :class:`Experiment` instances the user
        can only view.

        Returns
        -------
        `QuerySet`
        """
        if queryset is None:
            queryset = Experiment.objects.all()
        return instances_for_user_with_group_permission(
            user=self.user, queryset=queryset, group_type=GroupTypes.EDITOR
        )

    def editor_scoresets(self, queryset=None):
        """
        Return a list of :class:`ScoreSet` instances the user
        can only view.

        Returns
        -------
        `QuerySet`
        """
        if queryset is None:
            queryset = ScoreSet.objects.all()
        return instances_for_user_with_group_permission(
            user=self.user, queryset=queryset, group_type=GroupTypes.EDITOR
        )

    # Viewer
    # ---------------------------------------------------------------------- #
    def viewer_instances(self, queryset=None):
        """
        Return a list of :class:`DatasetModel` instances the user is a viewer
        for.

        Returns
        -------
        `list`
        """
        instances = (
            list(self.viewer_experimentsets(queryset))
            + list(self.viewer_experiments(queryset))
            + list(self.viewer_scoresets(queryset))
        )
        return instances

    def viewer_experimentsets(self, queryset=None):
        """
        Return a list of :class:`ExperimentSet` instances the user
        can only view.

        Returns
        -------
        `QuerySet`
        """
        if queryset is None:
            queryset = ExperimentSet.objects.all()
        return instances_for_user_with_group_permission(
            user=self.user, queryset=queryset, group_type=GroupTypes.VIEWER
        )

    def viewer_experiments(self, queryset=None):
        """
        Return a list of :class:`Experiment` instances the user
        can only view.

        Returns
        -------
        `QuerySet`
        """
        if queryset is None:
            queryset = Experiment.objects.all()
        return instances_for_user_with_group_permission(
            user=self.user, queryset=queryset, group_type=GroupTypes.VIEWER
        )

    def viewer_scoresets(self, queryset=None):
        """
        Return a list of :class:`ScoreSet` instances the user
        can only view.

        Returns
        -------
        `QuerySet`
        """
        if queryset is None:
            queryset = ScoreSet.objects.all()
        return instances_for_user_with_group_permission(
            user=self.user, queryset=queryset, group_type=GroupTypes.VIEWER
        )


# Post Save signals
# -------------------------------------------------------------------------- #
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Post-save signal invoked when a new user is saved/created. Creates a
    new profile for the user if this a first time call.
    """
    if created:
        email = None
        if instance.email:
            email = instance.email
        Profile.objects.create(user=instance, email=email)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Saves profile whenever associated user is saved.
    """
    if hasattr(instance, "profile"):
        instance.profile.save()
