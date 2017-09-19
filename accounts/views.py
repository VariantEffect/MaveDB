"""
Views for accounts app.
"""

import re
import json
import logging
import reversion

from django.conf import settings
from django.apps import apps
from django.db import transaction
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render, reverse, redirect, get_object_or_404

from django.contrib.auth import logout, get_user_model
import django.contrib.auth.views as auth_views
from django.contrib.auth.decorators import login_required, permission_required

from experiment.views import (
    ReferenceMappingFormSet,
    REFERENCE_MAPPING_FORM_PREFIX,
    parse_mapping_formset
)
from experiment.validators import EXP_ACCESSION_RE, EXPS_ACCESSION_RE
from experiment.forms import ExperimentEditForm, ExperimentForm
from scoreset.validators import SCS_ACCESSION_RE
from scoreset.forms import ScoreSetEditForm, ScoreSetForm

from main.fields import ModelSelectMultipleField as msmf
from main.utils.versioning import save_and_create_revision_if_tracked_changed

from .permissions import (
    GroupTypes,
    PermissionTypes,
    user_is_anonymous,
    user_is_admin_for_instance,
    user_is_contributor_for_instance,
    user_is_viewer_for_instance,
    update_admin_list_for_instance,
    update_contributor_list_for_instance,
    update_viewer_list_for_instance
)

from .forms import (
    RegistrationForm,
    SelectUsersForm,
    send_admin_email
)


User = get_user_model()
logger = logging.getLogger(name="django")
ExperimentSet = apps.get_model('experiment', 'ExperimentSet')
Experiment = apps.get_model('experiment', 'Experiment')
ScoreSet = apps.get_model('scoreset', 'ScoreSet')


# Utilities
# ------------------------------------------------------------------------- #
def get_class_for_accession(accession):
    """
    Returns the class matching the accession, if it's either 
    an `ExperimentSet`, `Experiment` or `ScoreSet` otherwise it 
    returns `None`.

    Parameters
    ----------
    accession : `str`
        The accession for an instance

    Returns
    -------
    `cls` or `None`
        A class that can be instantiated, or None.
    """
    if re.fullmatch(EXPS_ACCESSION_RE, accession):
        return ExperimentSet
    elif re.fullmatch(EXP_ACCESSION_RE, accession):
        return Experiment
    elif re.fullmatch(SCS_ACCESSION_RE, accession):
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
def manage_instance(request, accession):
    post_form = None
    context = {}

    try:
        klass = get_class_for_accession(accession)
        instance = get_object_or_404(klass, accession=accession)
    except:
        response = render(request, 'main/404_not_found.html')
        response.status_code = 404
        return response

    # 404 if there are no permissions instead of 403 to prevent
    # information leaking.
    has_permission = [
        user_is_admin_for_instance(request.user, instance),
    ]
    if not any(has_permission):
        response = render(request, 'main/404_not_found.html')
        response.status_code = 404
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
            return redirect("accounts:manage_instance", instance.accession)

    # Replace the form that has changed. If it reaches this point,
    # it means there were errors in the form.
    if post_form is not None and post_form.group == GroupTypes.ADMIN:
        context["admin_select_form"] = post_form
    elif post_form is not None and post_form.group == GroupTypes.VIEWER:
        context["viewer_select_form"] = post_form

    return render(request, "accounts/profile_manage.html", context)


@login_required(login_url=reverse_lazy("accounts:login"))
def edit_instance(request, accession):
    """
    This view takes uses the accession string to deduce the class belonging
    to that accession and then retrieves the appropriate instance or 404s.

    Once the instance has been retrieved, the correct edit form is retrieved
    and rendered to the user. POST form handling is delegated to the 
    appropriate method, which is a static method of edit form class.

    Only `Experiment` and `ScoreSet` can be edited. Passing an accession for
    `ExperimentSet` or `Variant` will return a 404.

    Parameters
    ----------
    accession : `str`
        A string object representing the accession of a database instance
        of either `Experiment` or `ScoreSet`.
    """
    try:
        klass = get_class_for_accession(accession)
        if klass not in [Experiment, ScoreSet]:
            raise TypeError("Can't edit class {}.".format(klass))
        instance = get_object_or_404(klass, accession=accession)
    except:
        response = render(request, 'main/404_not_found.html')
        response.status_code = 404
        return response

    has_permission = [
        user_is_admin_for_instance(request.user, instance),
    ]
    if not any(has_permission):
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
            " either `Experiment` or `ScoreSet`.".format(klass)
        )
        response = render(request, 'main/404_not_found.html')
        response.status_code = 404
        return response


def handle_scoreset_edit_form(request, instance):
    if not instance.private:
        form = ScoreSetEditForm(instance=instance)
    else:
        form = ScoreSetForm.PartialFormFromRequest(request, instance)

    context = {
        "edit_form": form,
        'instance': instance
    }

    if request.method == "POST":
        if not instance.private:
            form = ScoreSetEditForm(request.POST, instance=instance)
        else:
            form = ScoreSetForm.PartialFormFromRequest(request, instance)

        keywords = request.POST.getlist("keywords")
        keywords = [kw for kw in keywords if msmf.is_word(kw)]
        context["repop_keywords"] = ','.join(keywords)
        context["edit_form"] = form

        if form.is_valid():
            with transaction.atomic():
                updated_instance = form.save(commit=True)
                updated_instance.update_last_edit_info(request.user)
                save_and_create_revision_if_tracked_changed(
                    request.user, updated_instance
                )

            if request.POST.get("publish", None):
                updated_instance.publish()
                send_admin_email(request.user, updated_instance)

            return redirect(
                "accounts:edit_instance", updated_instance.accession
            )

    return render(request, 'accounts/profile_edit.html', context)


def handle_experiment_edit_form(request, instance):
    if not instance.private:
        form = ExperimentEditForm(instance=instance)
    else:
        form = ExperimentForm.PartialFormFromRequest(request, instance)

    # Set up the initial base context
    context = {"edit_form": form, 'instance': instance, 'experiment': True}

    # Set up the formset with initial data
    if instance.private:
        prev_reference_maps = instance.referencemapping_set.all()
        ref_mapping_formset = ReferenceMappingFormSet(
            initial=[r.to_json() for r in prev_reference_maps],
            prefix=REFERENCE_MAPPING_FORM_PREFIX
        )
        context["reference_mapping_formset"] = ref_mapping_formset

    # If you change the prefix arguments here, make sure to change them
    # in base.js as well for the +/- buttons to work correctly.
    if request.method == "POST":
        if not instance.private:
            form = ExperimentEditForm(request.POST, instance=instance)
        else:
            form = ExperimentForm.PartialFormFromRequest(request, instance)

        # Build the reference mapping formset
        if instance.private:
            ref_mapping_formset = ReferenceMappingFormSet(
                request.POST, prefix=REFERENCE_MAPPING_FORM_PREFIX,
                initial=[r.to_json() for r in prev_reference_maps]
            )
            context["reference_mapping_formset"] = ref_mapping_formset

        # Get the new keywords/accession/target org so that we can return
        # them for list repopulation if the form has errors.
        keywords = request.POST.getlist("keywords")
        keywords = [kw for kw in keywords if msmf.is_word(kw)]
        e_accessions = request.POST.getlist("external_accessions")
        e_accessions = [ea for ea in e_accessions if msmf.is_word(ea)]
        target_organism = request.POST.getlist("target_organism")
        target_organism = [to for to in target_organism if msmf.is_word(to)]

        # Set the context
        context["edit_form"] = form
        context["repop_keywords"] = ','.join(keywords)
        context["repop_external_accessions"] = ','.join(e_accessions)
        context["repop_target_organism"] = ','.join(target_organism)

        if form.is_valid():
            if instance.private:
                maps = parse_mapping_formset(ref_mapping_formset)
                if not all([m is not None for m in maps]):
                    return render(
                        request, 'accounts/profile_edit.html', context
                    )

                with transaction.atomic():
                    updated_instance = form.save(commit=True)
                    updated_instance.update_last_edit_info(request.user)
                    save_and_create_revision_if_tracked_changed(
                        request.user, updated_instance
                    )
                    prev_reference_maps.delete()
                    for ref_map in maps:
                        ref_map.experiment = updated_instance
                        ref_map.save()
            else:
                with transaction.atomic():
                    updated_instance = form.save(commit=True)
                    updated_instance.update_last_edit_info(request.user)
                    save_and_create_revision_if_tracked_changed(
                        request.user, updated_instance
                    )

            return redirect(
                "accounts:edit_instance", updated_instance.accession
            )

    return render(request, 'accounts/profile_edit.html', context)


@login_required(login_url=reverse_lazy("accounts:login"))
def view_instance(request, accession):
    """
    This view takes uses the accession string to deduce the class belonging
    to that accession and then retrieves the appropriate instance or 404s.

    Once the instance has been retrieved, the user is redirected to the
    appropriate view.

    Parameters
    ----------
    accession : `str`
        A string object representing the accession of a database instance.
    """
    try:
        klass = get_class_for_accession(accession)
        instance = get_object_or_404(klass, accession=accession)
    except:
        response = render(request, 'main/404_not_found.html')
        response.status_code = 404
        return response

    has_permission = [
        user_is_admin_for_instance(request.user, instance),
        user_is_viewer_for_instance(request.user, instance)
    ]
    if not any(has_permission):
        response = render(request, 'main/404_not_found.html')
        response.status_code = 404
        return response

    if klass == Experiment:
        direct_to = "experiment:experiment_detail"
    elif klass == ExperimentSet:
        direct_to = "experiment:experimentset_detail"
    elif klass == ScoreSet:
        direct_to = "scoreset:scoreset_detail"
    else:
        response = render(request, "main/404_not_found.html")
        response.status_code = 404
        return response

    return redirect(direct_to, accession=instance.accession)


# Registration views
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
