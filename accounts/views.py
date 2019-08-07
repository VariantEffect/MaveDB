import logging

from formtools.wizard.views import SessionWizardView

import django.contrib.auth.views as auth_views
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse_lazy
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string


from accounts.utilities import delete, publish
from dataset.mixins import DatasetPermissionMixin
from urn.models import get_model_by_urn

from .forms import (
    RegistrationForm,
    SelectUsersForm,
    ProfileForm,
    ConfirmationForm,
)

User = get_user_model()
logger = logging.getLogger(name="django")
ExperimentSet = apps.get_model("dataset", "ExperimentSet")
Experiment = apps.get_model("dataset", "Experiment")
ScoreSet = apps.get_model("dataset", "ScoreSet")


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
    if request.is_ajax():
        profile = request.user.profile
        profile.generate_token()
        profile.save()
        return JsonResponse(
            {"token": profile.auth_token, "expiry": profile.auth_token_expiry}
        )

    if request.method == "POST":
        profile_form = ProfileForm(
            instance=request.user.profile, data=request.POST
        )
        if profile_form.is_valid():
            profile = profile_form.save(commit=True)
            messages.success(request, "Successfully updated your profile.")
            if profile.email:
                template_name = "accounts/confirm_email.html"
                message = render_to_string(
                    template_name, {"user": request.user}
                )
                request.user.profile.email_user(
                    subject="Profile email updated.", message=message
                )
                return HttpResponseRedirect(
                    reverse_lazy("accounts:profile_settings")
                )

    context = {"profile_form": profile_form}
    return render(request, "accounts/profile_settings.html", context)


@login_required(login_url=reverse_lazy("accounts:login"))
def profile_view(request):
    """
    The dashboard view. The only POST request this should receive is
    when a user requests for an instance to be deleted.
    """
    context = {}
    if request.method == "POST":
        delete_urn = request.POST.get("delete", False)
        publish_urn = request.POST.get("publish", False)
        if delete_urn:
            deleted = delete(delete_urn, request)
            if deleted:
                return HttpResponseRedirect(reverse_lazy("accounts:profile"))
        if publish_urn:
            published = publish(publish_urn, request)
            if published:
                return HttpResponseRedirect(reverse_lazy("accounts:profile"))
    return render(request, "accounts/profile_home.html", context)


class ManageDatasetUsersView(DatasetPermissionMixin, SessionWizardView):
    """
    Multi-step form view allowing a user to edit the group memberships
    for an instance.
    """

    # Second form is a dummy form for the confirmation step
    login_url = reverse_lazy("accounts:login")
    form_list = (
        ("manage_users", SelectUsersForm),
        ("confirm_changes", ConfirmationForm),
    )
    permission_required = "dataset.can_manage"
    templates = {
        "manage_users": "accounts/profile_manage.html",
        "confirm_changes": "accounts/contributor_summary.html",
    }

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(self.login_url)
        self.instance = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        try:
            instance = get_model_by_urn(self.kwargs.get("urn", None))
            if not isinstance(instance, (ExperimentSet, Experiment, ScoreSet)):
                raise Http404()
            return instance
        except ObjectDoesNotExist:
            raise Http404()

    def get_template_names(self):
        return self.templates[self.steps.current]

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == "confirm_changes":
            return kwargs
        kwargs["instance"] = self.instance
        return kwargs

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        context["all_data"] = self.get_all_cleaned_data()
        context["instance"] = self.instance
        return context

    def done(self, form_list, **kwargs):
        list(form_list)[0].process_user_list()
        messages.success(
            self.request,
            "Management updated for '{}'.".format(self.instance.urn),
        )
        return redirect("accounts:profile")


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
            return redirect("accounts:profile")

    context = {"form": form}
    return render(request, "registration/register.html", context)
