import re
import logging

from django.conf import settings
from django.apps import apps
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404

import django.contrib.auth.views as auth_views
from django.contrib.auth import logout, get_user_model
from django.contrib.auth.decorators import login_required

from urn.validators import (
    MAVEDB_EXPERIMENTSET_URN_PATTERN,
    MAVEDB_EXPERIMENT_URN_PATTERN,
    MAVEDB_SCORESET_URN_PATTERN
)

from .permissions import (
    GroupTypes, PermissionTypes, assign_superusers_as_admin
)
from .forms import (
    RegistrationForm,
    SelectUsersForm
)


User = get_user_model()
logger = logging.getLogger(name="django")
ExperimentSet = apps.get_model('dataset', 'ExperimentSet')
Experiment = apps.get_model('dataset', 'Experiment')
ScoreSet = apps.get_model('dataset', 'ScoreSet')


# Utilities
# ------------------------------------------------------------------------- #
def get_class_from_urn(urn):
    """
    Returns the class matching the urn, if it's either
    an `ExperimentSet`, `Experiment` or `ScoreSet` otherwise it 
    returns `None`.

    Parameters
    ----------
    urn : `str`
        The urn for an instance

    Returns
    -------
    `cls` or `None`
        A class that can be instantiated, or None.
    """
    if re.fullmatch(MAVEDB_EXPERIMENTSET_URN_PATTERN, urn):
        return ExperimentSet
    elif re.fullmatch(MAVEDB_EXPERIMENT_URN_PATTERN, urn):
        return Experiment
    elif re.fullmatch(MAVEDB_SCORESET_URN_PATTERN, urn):
        return ScoreSet
    else:
        return None


# Profile views
# ------------------------------------------------------------------------- #
def login_delegator(request):
    if settings.USE_SOCIAL_AUTH:
        return redirect("accounts:social:begin", "orcid")
    else:
        return auth_views.LoginView.as_view()(request)


def log_user_out(request):
    logout(request)
    return redirect("main:home")


def login_error(request):
    return render(request, "accounts/profile_create_error.html")


@login_required(login_url=reverse_lazy("accounts:login"))
def profile_view(request):
    """
    A simple view, at only one line...
    """
    return render(request, 'accounts/profile_home.html')


@login_required(login_url=reverse_lazy("accounts:login"))
def manage_instance(request, urn):
    post_form = None
    context = {}
    klass = get_class_from_urn(urn)
    if klass is None:
        raise Http404()
    instance = get_object_or_404(klass, urn=urn)

    has_permission = request.user.has_perm(
        PermissionTypes.CAN_MANAGE, instance)
    if not has_permission:
        raise PermissionDenied()

    # Initialise the forms with current group users.
    admin_select_form = SelectUsersForm(
        group=GroupTypes.ADMIN,
        user=request.user,
        instance=instance,
        required=True,
        prefix="administrator_management",
    )
    viewer_select_form = SelectUsersForm(
        group=GroupTypes.VIEWER,
        instance=instance,
        user=request.user,
        prefix="viewer_management",
    )

    context["instance"] = instance
    context["admin_select_form"] = admin_select_form
    context["viewer_select_form"] = viewer_select_form

    if request.method == "POST":
        # Hidden list in each form submission so we can determine which
        # form was submitted
        if 'administrators[]' in request.POST:
            post_form = SelectUsersForm(
                data=request.POST,
                user=request.user,
                group=GroupTypes.ADMIN,
                instance=instance,
                required=True,
                prefix="administrator_management"
            )
        elif 'viewers[]' in request.POST:
            post_form = SelectUsersForm(
                data=request.POST,
                user=request.user,
                group=GroupTypes.VIEWER,
                instance=instance,
                prefix="viewer_management"
            )

        if post_form is not None and post_form.is_valid():
            post_form.process_user_list()
            instance.last_edit_by = request.user
            assign_superusers_as_admin(instance)
            instance.save()
            messages.success(
                request, "Management updated for {}".format(instance.urn))
            return redirect("accounts:profile")

    # Replace the form that has changed. If it reaches this point,
    # it means there were errors in the form.
    if post_form is not None and post_form.group == GroupTypes.ADMIN:
        context["admin_select_form"] = post_form
    elif post_form is not None and post_form.group == GroupTypes.VIEWER:
        context["viewer_select_form"] = post_form

    return render(request, "accounts/profile_manage.html", context)


# Registration views [DEBUG MODE ONLY]
# ------------------------------------------------------------------------- #
def registration_view(request):
    form = RegistrationForm()
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True
            user.save()
            return redirect('accounts:profile')

    context = {'form': form}
    return render(request, 'registration/register.html', context)
