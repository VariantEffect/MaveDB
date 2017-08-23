"""
Views for accounts app.
"""

import re
import json

from django.apps import apps
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render, reverse, redirect, get_object_or_404

from django.contrib.auth import login
from django.contrib.auth.models import User, AnonymousUser, Group
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.sites.shortcuts import get_current_site

from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode

from experiment.validators import EXP_ACCESSION_RE, EXPS_ACCESSION_RE
from scoreset.validators import SCS_ACCESSION_RE
from scoreset.forms import ScoresetEditForm

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

from .tokens import account_activation_token
from .forms import (
    RegistrationForm,
    send_user_activation_email,
    SelectUsersForm
)

ExperimentSet = apps.get_model('experiment', 'ExperimentSet')
Experiment = apps.get_model('experiment', 'Experiment')
ScoreSet = apps.get_model('scoreset', 'ScoreSet')


def get_class_for_accession(accession):
    if re.fullmatch(EXPS_ACCESSION_RE, accession):
        return ExperimentSet
    elif re.fullmatch(EXP_ACCESSION_RE, accession):
        return Experiment
    elif re.fullmatch(SCS_ACCESSION_RE, accession):
        return ScoreSet
    else:
        return None


# Profile views
# ------------------------------------------------------------------------- #
@login_required(login_url=reverse_lazy("accounts:login"))
def profile_view(request):
    if user_is_anonymous(request.user):
        response = render(request, 'main/403_forbidden.html')
        response.status_code = 403
        return response
    return render(request, 'accounts/profile_home.html')


@login_required(login_url=reverse_lazy("accounts:login"))
def manage_instance(request, accession):
    klass = get_class_for_accession(accession)
    instance = get_object_or_404(klass, accession=accession)

    post_form = None
    context = {}
    context["instance"] = instance

    has_permission = [
        user_is_admin_for_instance(request.user, instance),
    ]
    if not any(has_permission):
        response = render(request, 'main/404_not_found.html')
        response.status_code = 404
        return response

    # Initialise the forms with current group users.
    admins = instance.administrators()
    contributors = instance.contributors()
    viewers = instance.viewers()
    admin_select_form = SelectUsersForm(
        initial={"users": [a.pk for a in admins]},
        group=GroupTypes.ADMIN,
        instance=instance,
        required=True,
        prefix="administrator_management"
    )
    contrib_select_form = SelectUsersForm(
        initial={"users": [c.pk for c in contributors]},
        group=GroupTypes.CONTRIBUTOR,
        instance=instance,
        prefix="contributor_management"
    )
    viewer_select_form = SelectUsersForm(
        initial={"users": [v.pk for v in viewers]},
        group=GroupTypes.VIEWER,
        instance=instance,
        prefix="viewer_management"
    )
    context["admin_select_form"] = admin_select_form
    context["contrib_select_form"] = contrib_select_form
    context["viewer_select_form"] = viewer_select_form

    if request.method == "POST":
        print(request.POST)
        if "administrator_management-users" in request.POST:
            post_form = SelectUsersForm(
                data=request.POST,
                group=GroupTypes.ADMIN,
                instance=instance,
                required=True,
                prefix="administrator_management"
            )
        elif "contributor_management-users" in request.POST:
            post_form = SelectUsersForm(
                data=request.POST,
                group=GroupTypes.CONTRIBUTOR,
                instance=instance,
                prefix="contributor_management"
            )
        elif "viewer_management-users" in request.POST:
            post_form = SelectUsersForm(
                data=request.POST,
                group=GroupTypes.VIEWER,
                instance=instance,
                prefix="viewer_management"
            )

        if post_form is not None and post_form.is_valid():
            post_form.process_user_list()
            return redirect("accounts:manage_instance", instance.accession)

    if post_form is not None and post_form.group == GroupTypes.ADMIN:
        context["admin_select_form"] = post_form
    elif post_form is not None and post_form.group == GroupTypes.CONTRIBUTOR:
        context["contrib_select_form"] = post_form
    elif post_form is not None and post_form.group == GroupTypes.VIEWER:
        context["viewer_select_form"] = post_form

    return render(request, "accounts/profile_manage.html", context)


@login_required(login_url=reverse_lazy("accounts:login"))
def edit_instance(request, accession):
    klass = get_class_for_accession(accession)
    instance = get_object_or_404(klass, accession=accession)
    has_permission = [
        user_is_admin_for_instance(request.user, instance),
        user_is_contributor_for_instance(request.user, instance),
    ]
    if not any(has_permission):
        response = render(request, 'main/404_not_found.html')
        response.status_code = 404
        return response

    form = ScoresetEditForm(instance=instance)
    context = {"form": form}

    if request.method == "POST":
        form = ScoresetEditForm(request.POST, instance=instance)
        if form.is_valid() and form.has_changed():
            updated_instance = form.save(commit=False)
            existing_keywords = instance.keywords.all()
            new_keywords = form.cleaned_data.get("keywords", [])
            for keyword in new_keywords:
                keyword.save()

            updated_instance.save()
            for keyword in new_keywords:
                updated_instance.keywords.add(keyword)
            for keyword in existing_keywords:
                if keyword not in new_keywords:
                    updated_instance.keywords.remove(keyword)

            return redirect(
                "accounts:edit_instance", updated_instance.accession
            )

    return render(request, 'accounts/profile_home.html', context)


@login_required(login_url=reverse_lazy("accounts:login"))
def view_instance(request, accession):
    klass = get_class_for_accession(accession)
    instance = get_object_or_404(klass, accession=accession)
    has_permission = [
        user_is_admin_for_instance(request.user, instance),
        user_is_contributor_for_instance(request.user, instance),
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

    return redirect(direct_to, accession=instance.accession)


# Registration views
# ------------------------------------------------------------------------- #
def activate_account_view(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        render(request, 'accounts/account_not_created.html')

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return redirect('accounts:profile')
    else:
        context = {'uidb64': uidb64}
        return render(request, 'accounts/activation_invalid.html', context)


def send_activation_email_view(request, uidb64):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is None:
        return render(request, 'accounts/account_not_created.html')

    # We have the User object, now try to send an email. If the new uidb64
    # or token could not be made, abort the send/resend cycle.
    uidb64, token = send_user_activation_email(
        uid=user.pk,
        secure=request.is_secure(),
        domain=get_current_site(request).domain,
        subject='Activate Your Account',
        template_name='accounts/activation_email.html')

    if uidb64 is None or token is None:
        return render(request, 'accounts/account_not_created.html')
    else:
        context = {'uidb64': uidb64}
        return render(request, 'accounts/activation_sent.html', context)


def registration_view(request):
    form = RegistrationForm()
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            # Additional hacked-on checking to see if email is unique.
            email = form.cleaned_data['email']

            if User.objects.filter(email__iexact=email).count() > 0:
                form.add_error(
                    "email", ValidationError("This email is already in use."))
            else:
                user = form.save(commit=False)
                user.is_active = False
                user.save()
                uidb64, token = send_user_activation_email(
                    uid=user.pk,
                    secure=request.is_secure(),
                    domain=get_current_site(request).domain,
                    subject='Activate Your Account',
                    template_name='accounts/activation_email.html')

                if uidb64 is None or token is None:
                    return render(
                        request,
                        'accounts/account_not_created.html'
                    )
                else:
                    context = {'uidb64': uidb64}
                    return render(
                        request,
                        'accounts/activation_sent.html',
                        context
                    )

    context = {'form': form}
    return render(request, 'accounts/register.html', context)
