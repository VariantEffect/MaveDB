import re
import logging
import json

from django.conf import settings
from django.apps import apps
from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404

import django.contrib.auth.views as auth_views
from django.contrib.auth import logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from dataset.forms.experiment import ExperimentEditForm, ExperimentForm
from dataset.forms.scoreset import ScoreSetEditForm, ScoreSetForm

from core.utilities import is_null, send_admin_email
from core.utilities.pandoc import convert_md_to_html
from core.utilities.versioning import track_changes

from genome.models import TargetGene
from genome.forms import TargetGeneForm, ReferenceMapForm, GenomicIntervalForm

from urn.validators import (
    MAVEDB_EXPERIMENTSET_URN_PATTERN,
    MAVEDB_EXPERIMENT_URN_PATTERN,
    MAVEDB_SCORESET_URN_PATTERN
)


from .permissions import GroupTypes, PermissionTypes, assign_superusers_as_admin
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
        response = render(request, 'main/403_forbidden.html')
        response.status_code = 403
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


def handle_scoreset_edit_form(request, instance):
    if not instance.private:
        form = ScoreSetEditForm(user=request.user, instance=instance)
        context = {'edit_form': form, 'instance': instance}

    else:
        scoreset = instance
        form = ScoreSetForm.from_request(request, instance)
        targetgene = scoreset.get_target()
        target_form = TargetGeneForm(user=request.user, instance=targetgene)

        # TODO: Multiple reference_maps/intervals
        reference_map = targetgene.get_reference_maps().first()
        reference_map_form = ReferenceMapForm(instance=reference_map)
        intervals = reference_map.get_intervals()
        interval_form = GenomicIntervalForm(instance=intervals[0])
        context = {
            'edit_form': form, 'instance': instance,
            'target_form': target_form, 'reference_map_form': reference_map_form,
            'interval_form': interval_form
        }

    # If the request is ajax, then it's for previewing the abstract
    # or method description. This code is coupled with base.js. Changes
    # here might break the javascript code.
    if request.is_ajax():
        markdown = request.GET.get("markdown", False)
        if not markdown:
            target_id = request.GET.get("targetId", "")
            try:
                targetgene = TargetGene.objects.get(pk=target_id)
                reference_map = targetgene.get_reference_maps().first()
                genome = reference_map.get_reference_genome()
                interval = reference_map.get_intervals().first()
                data = {
                    'targetName': targetgene.get_name(),
                    'wildTypeSequence': targetgene.get_wt_sequence_string(),
                    'referenceGenome': genome.id,
                    'isPrimary': reference_map.is_primary_reference_map(),
                    'intervalStart': interval.get_start(),
                    'intervalEnd': interval.get_end(),
                    'chromosome': interval.get_chromosome(),
                    'strand': interval.get_strand()
                }
            except AttributeError as e:
                data = {}
        else:
            data = {
                "abstractText": convert_md_to_html(
                    request.GET.get("abstractText", "")),
                "methodText": convert_md_to_html(
                    request.GET.get("methodText", ""))
            }

        return HttpResponse(
            json.dumps(data), content_type="application/json")

    if request.method == "POST":
        if not instance.private:
            form = ScoreSetEditForm(
                request.POST, user=request.user, instance=instance)
            valid = form.is_valid()
            context["edit_form"] = form
        else:
            target_form = TargetGeneForm(
                user=request.user, data=request.POST, instance=targetgene)
            reference_map_form = ReferenceMapForm(
                data=request.POST, instance=reference_map)
            interval_form = GenomicIntervalForm(
                data=request.POST, instance=intervals[0])
            form = ScoreSetForm.from_request(request, instance)

            context["edit_form"] = form
            context["target_form"] = target_form
            context["reference_map_form"] = reference_map_form
            context["interval_form"] = interval_form

            valid = all([
                form.is_valid(),
                target_form.is_valid(),
                reference_map_form.is_valid(),
                interval_form.is_valid()
            ])

        # Get the new keywords/urn/target org so that we can return
        # them for list repopulation if the form has errors.
        keywords = request.POST.getlist("keywords")
        keywords = [kw for kw in keywords if not is_null(kw)]

        sra_ids = request.POST.getlist("sra_ids")
        sra_ids = [i for i in sra_ids if not is_null(sra_ids)]

        doi_ids = request.POST.getlist("doi_ids")
        doi_ids = [i for i in doi_ids if not is_null(doi_ids)]

        pubmed_ids = request.POST.getlist("pubmed_ids")
        pubmed_ids = [i for i in pubmed_ids if not is_null(pubmed_ids)]

        # Set the context
        context["repop_keywords"] = ','.join(keywords)
        context["repop_sra_identifiers"] = ','.join(sra_ids)
        context["repop_doi_identifiers"] = ','.join(doi_ids)
        context["repop_pubmed_identifiers"] = ','.join(pubmed_ids)

        if valid:
            if instance.private:
                updated_instance = form.save(commit=True)

                target_form.instance.scoreset = updated_instance
                targetgene = target_form.save(commit=True)

                reference_map_form.instance.target = targetgene
                reference_map = reference_map_form.save(commit=True)

                interval_form.instance.reference_map = reference_map
                interval_form.save(commit=True)

            else:
                updated_instance = form.save(commit=True)

            track_changes(request.user, updated_instance)
            if request.POST.get("publish", None):
                updated_instance.publish(propagate=True)
                updated_instance.set_modified_by(request.user, propagate=True)
                updated_instance.save(save_parents=True)
                track_changes(
                    request.user, updated_instance)
                send_admin_email(request.user, updated_instance)

            messages.success(
                request, "{} successfully updated!".format(instance.urn))
            return redirect("accounts:profile")

    return render(request, 'accounts/profile_edit.html', context)


def handle_experiment_edit_form(request, instance):
    if not instance.private:
        form = ExperimentEditForm(user=request.user, instance=instance)
    else:
        form = ExperimentForm.from_request(request, instance)

    # Set up the initial base context
    context = {"edit_form": form, 'instance': instance, 'experiment': True}

    # If the request is ajax, then it's for previewing the abstract
    # or method description. This code is coupled with base.js. Changes
    # here might break the javascript code.
    if request.is_ajax():
        data = dict()
        data['abstractText'] = convert_md_to_html(
            request.GET.get("abstractText", "")
        )
        data['methodText'] = convert_md_to_html(
            request.GET.get("methodText", "")
        )
        return HttpResponse(json.dumps(data), content_type="application/json")

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

        pubmed_ids = request.POST.getlist("pubmed_ids")
        pubmed_ids = [i for i in pubmed_ids if not is_null(pubmed_ids)]

        # Set the context
        context["edit_form"] = form
        context["repop_keywords"] = ','.join(keywords)
        context["repop_sra_identifiers"] = ','.join(sra_ids)
        context["repop_doi_identifiers"] = ','.join(doi_ids)
        context["repop_pubmed_identifiers"] = ','.join(pubmed_ids)

        if form.is_valid():
            updated_instance = form.save(commit=True)
            track_changes(request.user, updated_instance)
            messages.success(
                request, "{} successfully updated!".format(instance.urn))
            return redirect("accounts:profile")

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
