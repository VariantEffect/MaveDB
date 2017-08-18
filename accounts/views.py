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
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site

from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode

from guardian.shortcuts import get_objects_for_user
from guardian.conf.settings import ANONYMOUS_USER_NAME

from experiment.validators import EXP_ACCESSION_RE, EXPS_ACCESSION_RE
from scoreset.validators import SCS_ACCESSION_RE

from .models import (
    user_is_admin_for_instance,
    user_is_contributor_for_instance,
    user_is_viewer_for_instance,
    update_admin_list_for_instance,
    update_contributor_list_for_instance,
    update_viewer_list_for_instance
)

from .tokens import account_activation_token
from .forms import RegistrationForm, send_user_activation_email

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


def get_base_context_for_profile(request):
    experimentsets = get_objects_for_user(
        request.user, perms=[], any_perm=False, klass=ExperimentSet)
    experiments = get_objects_for_user(
        request.user, perms=[], any_perm=False, klass=Experiment)
    scoresets = get_objects_for_user(
        request.user, perms=[], any_perm=False, klass=ScoreSet)
    return {
        "experimentsets": experimentsets,
        "experiments": experiments,
        "scoresets": scoresets,
    }


@login_required(login_url=reverse_lazy("accounts:login"))
def manage_instance(request, accession):
    context = get_base_context_for_profile(request)
    klass = get_class_for_accession(accession)

    instance = get_object_or_404(klass, accession=accession)
    site_users = User.objects.all()
    instance_admins = []
    instance_contributors = []
    instance_viewers = []
    selectable_users = []

    print(request.user.username)
    print(context)
    print(user_is_admin_for_instance(request.user, instance))

    if request.is_ajax():
        usernames = request.POST.getlist("usernames[]")
        group_type = request.POST["type"]
        if not usernames:
            response = {"error": "There must be at least one administrator"}
            return HttpResponse(json.dumps(response))

        try:
            if group_type == "administrators":
                update_admin_list_for_instance(usernames, instance)
            elif group_type == "contributors":
                update_contributor_list_for_instance(usernames, instance)
            elif group_type == "viewers":
                update_viewer_list_for_instance(usernames, instance)
            else:
                raise ValueError(
                    "Group type {} not recognised.".format(group_type))
        except (ValueError, ObjectDoesNotExist) as e:
            response = {"error": str(e)}
            return HttpResponse(json.dumps(response))

        for user in site_users:
            if user.username == ANONYMOUS_USER_NAME:
                continue
            if user_is_admin_for_instance(user, instance):
                instance_admins.append(user)
            else:
                selectable_users.append(user)

        response = {
            "success": "Saved successfully!",
            "left": [u.username for u in selectable_users],
            "right": [u.username for u in instance_admins]
        }
        return HttpResponse(json.dumps(response))

    if klass is None:
        get_object_or_404(Experiment, accession="fail")

    for user in site_users:
        if user.username == ANONYMOUS_USER_NAME:
            continue
        if user_is_admin_for_instance(user, instance):
            instance_admins.append(user)
        elif user_is_contributor_for_instance(user, instance):
            instance_contributors.append(user)
        elif user_is_viewer_for_instance(user, instance):
            instance_viewers.append(user)
        else:
            selectable_users.append(user)

    request.user.save()
    context["admins"] = instance_admins
    context["contributors"] = instance_contributors
    context["viewers"] = instance_viewers
    context["selectable"] = selectable_users

    return render(request, "accounts/profile_manage.html", context)


@login_required(login_url=reverse_lazy("accounts:login"))
def profile_view(request):
    user = request.user
    context = get_base_context_for_profile(request)
    experimentsets = context["experimentsets"]
    experiments = context["experiments"]
    scoresets = context["scoresets"]

    admin_models = []
    contrib_models = []
    viewer_models = []

    for instance in experimentsets:
        if user_is_admin_for_instance(user, instance):
            admin_models.append(instance)
        if user_is_contributor_for_instance(user, instance):
            contrib_models.append(instance)
        if user_is_viewer_for_instance(user, instance):
            viewer_models.append(instance)

    for instance in experiments:
        if user_is_admin_for_instance(user, instance):
            admin_models.append(instance)
        if user_is_contributor_for_instance(user, instance):
            contrib_models.append(instance)
        if user_is_viewer_for_instance(user, instance):
            viewer_models.append(instance)

    for instance in scoresets:
        if user_is_admin_for_instance(user, instance):
            admin_models.append(instance)
        if user_is_contributor_for_instance(user, instance):
            contrib_models.append(instance)
        if user_is_viewer_for_instance(user, instance):
            viewer_models.append(instance)

    context["administrator_models"] = admin_models
    context["contributor_models"] = contrib_models
    context["viewer_models"] = viewer_models
    return render(request, 'accounts/profile_home.html', context)


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
                    return render(request, 'accounts/account_not_created.html')
                else:
                    context = {'uidb64': uidb64}
                    return render(request, 'accounts/activation_sent.html', context)

    context = {'form': form}
    return render(request, 'accounts/register.html', context)
