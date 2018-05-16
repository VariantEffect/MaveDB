import logging

from social_django.models import UserSocialAuth

from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.db import models
from django.db.models import QuerySet
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.html import format_html

from core.models import TimeStampedModel

from dataset.models.experimentset import ExperimentSet
from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet

from .permissions import (
    GroupTypes,
    user_is_anonymous,
    instances_for_user_with_group_permission
)


logger = logging.getLogger('django')


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
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email = models.EmailField(default=None, blank=True, null=True)
    
    def email_user(self, message, subject, from_email=None, **kwargs):
        email = self.email or self.user.email
        if email:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[email],
                **kwargs
            )
        else:
            logger.error(
                "Tried email user {} from Profile but could not find an "
                "email address.".format(self.user.username)
            )
        
    @property
    def unique_name(self):
        return '{} | {}'.format(self.get_display_name(), self.user.username)

    @classmethod
    def non_anonymous_profiles(cls):
        """Returns a list of all non-anonymous profiles."""
        return [p for p in cls.objects.all() if not p.is_anon()]

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
            return 'https://orcid.org/{}'.format(self.user.username)

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
            return 'anonymous user'
        else:
            return format_html('<a href="{url}">{name}</a>'.format(
                url=self.get_orcid_url(),
                name=self.get_display_name()))

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
            return 'anonymous user'
        else:
            return format_html('<a href="{url}">{name}</a>'.format(
                url=self.get_orcid_url(),
                name=self.get_full_name()))

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
            self.user).first()
        if not isinstance(social_auth, UserSocialAuth):
            return self.get_full_name()
        else:
            credit_name = social_auth.extra_data.get('credit-name', None)
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
            return '{} {}'.format(
                self.user.first_name.capitalize(),
                self.user.last_name.capitalize()
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
            return '{}, {}'.format(
                self.user.last_name.capitalize(),
                self.user.first_name[0].capitalize()
            )

    def __str__(self):
        return "{}_profile".format(self.user.username)

    @staticmethod
    def _iterable_to_queryset(iterable, klass):
        pks = set([i.pk for i in iterable])
        return klass.objects.filter(pk__in=pks).order_by('-modification_date')

    # Contributor
    # ----------------------------------------------------------------------- #
    def contributor_instances(self):
        """
        Return a list of :class:`DatasetModel` instances the user is a
        contributor for (view, edit, or admin).

        Returns
        -------
        `list`
        """
        instances = list(self.contributor_experimentsets()) + \
            list(self.contributor_experiments()) + \
            list(self.contributor_scoresets())
        return instances

    def contributor_experimentsets(self):
        """
        Return a list of :class:`ExperimentSet` instances the user
        contributes to.

        Returns
        -------
        `QuerySet`
        """
        instances = self.administrator_experimentsets() | \
            self.editor_experimentsets() | \
            self.viewer_experimentsets()
        return instances.all()

    def contributor_experiments(self):
        """
        Return a list of :class:`Experiment` instances the user
        contributes to.

        Returns
        -------
        `QuerySet`
        """
        instances = self.administrator_experiments() | \
            self.editor_experiments() | \
            self.viewer_experiments()
        return instances.all()

    def contributor_scoresets(self):
        """
        Return a list of :class:`ScoreSet` instances the user
        contributes to.

        Returns
        -------
        `QuerySet`
        """
        instances = self.administrator_scoresets() | \
            self.editor_scoresets() | \
            self.viewer_scoresets()
        return instances.all()

    def public_contributor_experimentsets(self):
        """Filters out private experimentsets"""
        instances = self.contributor_experimentsets().exclude(private=True)
        return instances.all()

    def public_contributor_experiments(self):
        """Filters out private experiments"""
        instances = self.contributor_experiments().exclude(private=True)
        return instances.all()

    def public_contributor_scoresets(self):
        """Filters out private scoresets"""
        instances = self.contributor_scoresets().exclude(private=True)
        return instances.all()

    # Administrator
    # ----------------------------------------------------------------------- #
    def administrator_instances(self):
        """
        Return a list of :class:`DatasetModel` instances the user is an admin
        for.

        Returns
        -------
        `list`
        """
        instances = list(self.administrator_experimentsets()) + \
            list(self.administrator_experiments()) + \
            list(self.administrator_scoresets())
        return instances

    def administrator_experimentsets(self):
        """
        Return a list of :class:`ExperimentSet` instances the user
        administrates.

        Returns
        -------
        `QuerySet`
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ExperimentSet,
            group_type=GroupTypes.ADMIN
        )

    def administrator_experiments(self):
        """
        Return a list of :class:`Experiment` instances the user
        administrates.

        Returns
        -------
        `QuerySet`
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=Experiment,
            group_type=GroupTypes.ADMIN
        )

    def administrator_scoresets(self):
        """
        Return a list of :class:`Experiment` instances the user
        administrates.

        Returns
        -------
        `QuerySet`
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ScoreSet,
            group_type=GroupTypes.ADMIN
        )

    # Editor
    # ---------------------------------------------------------------------- #
    def editor_instances(self):
        """
        Return a list of :class:`DatasetModel` instances the user is a viewer
        for.

        Returns
        -------
        `QuerySet`
        """
        instances = list(self.editor_experimentsets()) + \
            list(self.editor_experiments()) + \
            list(self.editor_scoresets())
        return instances

    def editor_experimentsets(self):
        """
        Return a list of :class:`ExperimentSet` instances the user
        can only view.

        Returns
        -------
        `QuerySet`
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ExperimentSet,
            group_type=GroupTypes.EDITOR
        )

    def editor_experiments(self):
        """
        Return a list of :class:`Experiment` instances the user
        can only view.

        Returns
        -------
        `QuerySet`
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=Experiment,
            group_type=GroupTypes.EDITOR
        )

    def editor_scoresets(self):
        """
        Return a list of :class:`ScoreSet` instances the user
        can only view.

        Returns
        -------
        `QuerySet`
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ScoreSet,
            group_type=GroupTypes.EDITOR
        )

    # Viewer
    # ---------------------------------------------------------------------- #
    def viewer_instances(self):
        """
        Return a list of :class:`DatasetModel` instances the user is a viewer
        for.

        Returns
        -------
        `list`
        """
        instances = list(self.viewer_experimentsets()) + \
            list(self.viewer_experiments()) + \
            list(self.viewer_scoresets())
        return instances

    def viewer_experimentsets(self):
        """
        Return a list of :class:`ExperimentSet` instances the user
        can only view.

        Returns
        -------
        `QuerySet`
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ExperimentSet,
            group_type=GroupTypes.VIEWER
        )

    def viewer_experiments(self):
        """
        Return a list of :class:`Experiment` instances the user
        can only view.

        Returns
        -------
        `QuerySet`
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=Experiment,
            group_type=GroupTypes.VIEWER
        )

    def viewer_scoresets(self):
        """
        Return a list of :class:`ScoreSet` instances the user
        can only view.

        Returns
        -------
        `QuerySet`
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ScoreSet,
            group_type=GroupTypes.VIEWER
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
    instance.profile.save()
