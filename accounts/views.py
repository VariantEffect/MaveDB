import logging

import django.contrib.auth.views as auth_views
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.mail import send_mail
from django.core.urlresolvers import reverse_lazy
from django.http import Http404
from django.shortcuts import render, redirect
from django.template.loader import render_to_string

from accounts.utilities import delete, publish
from main.context_processors import baseurl
from urn.models import get_model_by_urn
from .forms import (
    RegistrationForm,
    SelectUsersForm,
    ProfileForm
)
from .permissions import (
    GroupTypes, PermissionTypes, assign_superusers_as_admin
)

User = get_user_model()
logger = logging.getLogger(name="django")
ExperimentSet = apps.get_model('dataset', 'ExperimentSet')
Experiment = apps.get_model('dataset', 'Experiment')
ScoreSet = apps.get_model('dataset', 'ScoreSet')


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
def profile_settings(request):
    """
    Management of the user's `ProfileForm`. Currently only allows an email
    address to be set.
    """
    profile_form = ProfileForm(instance=request.user.profile)
    if request.method == "POST":
        profile_form = ProfileForm(
                instance=request.user.profile, data=request.POST)
        if profile_form.is_valid():
            profile = profile_form.save(commit=True)
            messages.success(request, "Successfully updated your profile.")
            if profile.email:
                template_name = "accounts/confirm_email.html"
                message = render_to_string(template_name, {
                    'user': request.user,
                })
                send_mail(
                    subject='Confirm email update.',
                    message=message,
                    from_email=None,
                    recipient_list=[profile.email]
                )
        else:
            messages.error(
                request,
                "There were errors with your submission. "
                "Check the profile tab for more detail."
            )

    context = {"profile_form": profile_form}
    return render(request, 'accounts/profile_settings.html', context)


@login_required(login_url=reverse_lazy("accounts:login"))
def profile_view(request):
    """
    The dashboard view. The only POST request this should receive is
    when a user requests for an instance to be deleted.
    """
    context = {}
    if request.method == 'POST':
        delete_urn = request.POST.get("delete", False)
        publish_urn = request.POST.get("publish", False)
        if delete_urn:
            delete(delete_urn, request)
        if publish_urn:
            publish(publish_urn, request)
    return render(request, 'accounts/profile_home.html', context)


@login_required(login_url=reverse_lazy("accounts:login"))
def manage_instance(request, urn):
    post_form = None
    context = {}
    try:
        instance = get_model_by_urn(urn=urn)
    except ObjectDoesNotExist:
        raise Http404()

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
        prefix="{}_management".format(GroupTypes.ADMIN),
    )
    editor_select_form = SelectUsersForm(
        group=GroupTypes.EDITOR,
        instance=instance,
        user=request.user,
        prefix="{}_management".format(GroupTypes.EDITOR),
    )
    viewer_select_form = SelectUsersForm(
        group=GroupTypes.VIEWER,
        instance=instance,
        user=request.user,
        prefix="{}_management".format(GroupTypes.VIEWER),
    )

    context["instance"] = instance
    context['group_types'] = GroupTypes
    context["admin_select_form"] = admin_select_form
    context["editor_select_form"] = editor_select_form
    context["viewer_select_form"] = viewer_select_form

    if request.method == "POST":
        # Hidden list in each form submission so we can determine which
        # form was submitted
        if '{}[]'.format(GroupTypes.ADMIN) in request.POST:
            post_form = SelectUsersForm(
                data=request.POST,
                user=request.user,
                group=GroupTypes.ADMIN,
                instance=instance,
                required=True,
                prefix="{}_management".format(GroupTypes.ADMIN)
            )
        elif '{}[]'.format(GroupTypes.EDITOR) in request.POST:
            post_form = SelectUsersForm(
                data=request.POST,
                user=request.user,
                group=GroupTypes.EDITOR,
                instance=instance,
                prefix="{}_management".format(GroupTypes.EDITOR)
            )
        elif '{}[]'.format(GroupTypes.VIEWER) in request.POST:
            post_form = SelectUsersForm(
                data=request.POST,
                user=request.user,
                group=GroupTypes.VIEWER,
                instance=instance,
                prefix="{}_management".format(GroupTypes.VIEWER)
            )

        if post_form is not None and post_form.is_valid():
            base_url = baseurl(request)['BASE_URL']
            post_form.process_user_list(base_url)
            instance.last_edit_by = request.user
            assign_superusers_as_admin(instance)
            instance.save()
            messages.success(
                request, "Management updated for {}.".format(instance.urn))
            return redirect("accounts:profile")
        else:
            messages.error(
                request,
                "Could not update {} management changes. "
                "Check your submission for errors.".format(instance.urn))

    # Replace the form that has changed. If it reaches this point,
    # it means there were errors in the form.
    if post_form is not None and post_form.group == GroupTypes.ADMIN:
        context["admin_select_form"] = post_form
    elif post_form is not None and post_form.group == GroupTypes.EDITOR:
        context["editor_select_form"] = post_form
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
