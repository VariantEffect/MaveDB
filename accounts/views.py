"""
Views for accounts app.
"""

import re
import logging

from django.conf import settings
from django.apps import apps
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404

import django.contrib.auth.views as auth_views
from django.contrib.auth import logout, get_user_model
from django.contrib.auth.decorators import login_required

from dataset.forms.experiment import ExperimentEditForm, ExperimentForm
from dataset.forms.scoreset import ScoreSetEditForm, ScoreSetForm

from urn.validators import (
    MAVEDB_EXPERIMENTSET_URN_PATTERN,
    MAVEDB_EXPERIMENT_URN_PATTERN,
    MAVEDB_SCORESET_URN_PATTERN
)

from main.utils import is_null
from main.utils.versioning import save_and_create_revision_if_tracked_changed

from .permissions import (
    GroupTypes,
    PermissionTypes,
    user_is_anonymous
)

from .forms import (
    RegistrationForm,
    SelectUsersForm,
    send_admin_email
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


# List Users
# ------------------------------------------------------------------------- #
def list_all_users_and_their_data(request):
    users = [
        user for user in User.objects.all()
        if not (user_is_anonymous(user) or user.is_superuser)
    ]

    # Filter out users that are not associated with any public datasets
    users = [
        user for user in users
        if any(not i.private for i in user.profile.administrator_instances())
    ]

    # Handle the pagination request options
    try:
        per_page = request.GET.get('per-page', 25)
        per_page = int(per_page)
        paginator = Paginator(users, per_page=per_page)
    except (PageNotAnInteger, ValueError, EmptyPage):
        per_page = 25
        paginator = Paginator(users, per_page=per_page)

    try:
        page_num = request.GET.get('page', 1)
        users = paginator.page(page_num)
    except PageNotAnInteger:
        page_num = 1
        users = paginator.page(page_num)
    except EmptyPage:
        page_num = paginator.num_pages
        users = paginator.page(page_num)

    context = {
        "users": users,
        "per_page": per_page,
        "page_num": page_num,
        "per_page_selections": [25, 50, 100]
    }
    return render(
        request, "accounts/list_all.html", context
    )


# Profile views
# ------------------------------------------------------------------------- #
def login_delegator(request):
    if settings.USE_SOCIAL_AUTH:
        return redirect("accounts:social:begin", "orcid")
    else:
        print("debug login")
        return auth_views.LoginView.as_view()(request)


def log_user_out(request):
    logout(request)
    return redirect("main:home")


def login_error(request):
    return render(request, "accounts/account_not_created.html")


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

    try:
        klass = get_class_from_urn(urn)
        instance = get_object_or_404(klass, urn=urn)
    except:
        response = render(request, 'main/404_not_found.html')
        response.status_code = 404
        return response

    # 404 if there are no permissions instead of 403 to prevent
    # information leaking.
    has_permission = request.user.has_perm(PermissionTypes.CAN_MANAGE, instance)
    if not has_permission:
        response = render(request, 'main/403_forbidden.html')
        response.status_code = 403
        return response

    # Initialise the forms with current group users.
    admin_select_form = SelectUsersForm(
        group=GroupTypes.ADMIN,
        instance=instance,
        required=True,
        prefix="administrator_management"
    )
    viewer_select_form = SelectUsersForm(
        group=GroupTypes.VIEWER,
        instance=instance,
        prefix="viewer_management"
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
                group=GroupTypes.ADMIN,
                instance=instance,
                required=True,
                prefix="administrator_management"
            )
        elif 'viewers[]' in request.POST:
            post_form = SelectUsersForm(
                data=request.POST,
                group=GroupTypes.VIEWER,
                instance=instance,
                prefix="viewer_management"
            )

        if post_form is not None and post_form.is_valid():
            post_form.process_user_list()
            instance.last_edit_by = request.user
            instance.save()
            return redirect("accounts:manage_instance", instance.urn)

    # Replace the form that has changed. If it reaches this point,
    # it means there were errors in the form.
    if post_form is not None and post_form.group == GroupTypes.ADMIN:
        context["admin_select_form"] = post_form
    elif post_form is not None and post_form.group == GroupTypes.VIEWER:
        context["viewer_select_form"] = post_form

    return render(request, "accounts/profile_manage.html", context)


@login_required(login_url=reverse_lazy("accounts:login"))
def edit_instance(request, urn):
    """
    This view takes uses the urn string to deduce the class belonging
    to that urn and then retrieves the appropriate instance or 404s.

    Once the instance has been retrieved, the correct edit form is retrieved
    and rendered to the user. POST form handling is delegated to the 
    appropriate method, which is a static method of edit form class.

    Only `Experiment` and `ScoreSet` can be edited. Passing an urn for
    `ExperimentSet` or `Variant` will return a 404.

    Parameters
    ----------
    urn : `str`
        A string object representing the urn of a database instance
        of either `Experiment` or `ScoreSet`.
    """
    try:
        klass = get_class_from_urn(urn)
        if klass not in [Experiment, ScoreSet]:
            raise TypeError("Can't edit class {}.".format(klass))
        instance = get_object_or_404(klass, urn=urn)
    except:
        response = render(request, 'main/404_not_found.html')
        response.status_code = 404
        return response

    has_permission = request.user.has_perm(PermissionTypes.CAN_EDIT, instance)
    if not has_permission:
        response = render(request, 'main/404_not_found.html')
        response.status_code = 404
        return response

    if klass == Experiment:
        return handle_experiment_edit_form(request, instance)
    elif klass == ScoreSet:
        return handle_scoreset_edit_form(request, instance)
    else:
        logger.error(
            "Tried to process an edit form for an invalid type {}. Expecting "
            "either `Experiment` or `ScoreSet`.".format(klass))
        response = render(request, 'main/404_not_found.html')
        response.status_code = 404
        return response


@transaction.atomic
def handle_scoreset_edit_form(request, instance):
    if not instance.private:
        form = ScoreSetEditForm(user=request.user, instance=instance)
    else:
        form = ScoreSetForm.from_request(request, instance)
    context = {'edit_form': form, 'instance': instance}

    if request.method == "POST":
        if not instance.private:
            form = ScoreSetEditForm(
                request.POST, user=request.user, instance=instance)
        else:
            form = ScoreSetForm.from_request(request, instance)

        if form.is_valid():
            updated_instance = form.save(commit=True)
            # save_and_create_revision_if_tracked_changed(
            #     request.user, updated_instance)
            if request.POST.get("publish", None):
                updated_instance.publish(propagate=True)
                updated_instance.set_last_edit_by(request.user, propagate=True)
                updated_instance.save(save_parents=True)
                send_admin_email(request.user, updated_instance)
            return redirect("accounts:edit_instance", updated_instance.urn)
        else:
            keywords = request.POST.getlist("keywords")
            keywords = [kw for kw in keywords]
            context["repop_keywords"] = ','.join(keywords)
            context["edit_form"] = form

    return render(request, 'accounts/profile_edit.html', context)


@transaction.atomic
def handle_experiment_edit_form(request, instance):
    if not instance.private:
        form = ExperimentEditForm(user=request.user, instance=instance)
    else:
        form = ExperimentForm.from_request(request, instance)

    # Set up the initial base context
    context = {"edit_form": form, 'instance': instance, 'experiment': True}

    # If you change the context arguments here, make sure to change them
    # in base.js as well.
    if request.method == "POST":
        if not instance.private:
            form = ExperimentEditForm(
                request.POST, user=request.user, instance=instance)
        else:
            form = ExperimentForm.from_request(request, instance)

        # Get the new keywords/urn/target org so that we can return
        # them for list repopulation if the form has errors.
        keywords = request.POST.getlist("keywords")
        keywords = [kw for kw in keywords if not is_null(kw)]

        sra_ids = request.POST.getlist("sra_ids")
        sra_ids = [i for i in sra_ids if not is_null(sra_ids)]

        doi_ids = request.POST.getlist("doi_ids")
        doi_ids = [i for i in doi_ids if not is_null(doi_ids)]

        pubmed_ids = request.POST.getlist("pmid_ids")
        pubmed_ids = [i for i in pubmed_ids if not is_null(pubmed_ids)]

        target_organism = request.POST.getlist("target_organism")
        target_organism = [to for to in target_organism if not is_null(to)]

        # Set the context
        context["edit_form"] = form
        context["repop_keywords"] = ','.join(keywords)
        context["repop_sra_identifiers"] = ','.join(sra_ids)
        context["repop_doi_identifiers"] = ','.join(doi_ids)
        context["repop_pubmed_identifiers"] = ','.join(pubmed_ids)
        context["repop_target_organism"] = ','.join(target_organism)

        if form.is_valid():
            updated_instance = form.save(commit=True)
            # save_and_create_revision_if_tracked_changed(
            #     request.user, updated_instance)
            return redirect("accounts:edit_instance", updated_instance.urn)

    return render(request, 'accounts/profile_edit.html', context)


@login_required(login_url=reverse_lazy("accounts:login"))
def view_instance(request, urn):
    """
    This view takes uses the urn string to deduce the class belonging
    to that urn and then retrieves the appropriate instance or 404s.

    Once the instance has been retrieved, the user is redirected to the
    appropriate view.

    Parameters
    ----------
    urn : `str`
        A string object representing the urn of a database instance.
    """
    try:
        klass = get_class_from_urn(urn)
        instance = get_object_or_404(klass, urn=urn)
    except:
        response = render(request, 'main/404_not_found.html')
        response.status_code = 404
        return response

    has_permission = request.user.has_perm(PermissionTypes.CAN_VIEW, instance)
    if not has_permission:
        response = render(request, 'main/403_forbidden.html')
        response.status_code = 403
        return response

    if klass == Experiment:
        direct_to = "dataset:experiment_detail"
    elif klass == ExperimentSet:
        direct_to = "dataset:experimentset_detail"
    elif klass == ScoreSet:
        direct_to = "dataset:scoreset_detail"
    else:
        response = render(request, "main/404_not_found.html")
        response.status_code = 404
        return response

    return redirect(direct_to, urn=instance.urn)


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
