from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.urlresolvers import reverse_lazy
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

from accounts.models import User
from dataset import constants
from dataset.models.scoreset import ScoreSet
from main.models import News
from manager.models import Role
from urn.models import get_model_by_urn

from .forms import AddPmidForm, AddUserForm, CreateNewsForm, SetUserRoleForm


def _default_context():
    subcommand_keys = ["addpmid", "adduser", "createnews", "setuserrole"]
    return {
        "subcommands": {
            s_k: reverse(f"manager:manage_{s_k}") for s_k in subcommand_keys
        }
    }


def _update_context_with_invalid_errors(context, form_errors):
    first_invalid_field = sorted(form_errors.keys())[0]
    first_invalid_field_message = form_errors[first_invalid_field][0]
    result_message = "Error."
    result_message_details = (
        f"{first_invalid_field}: {first_invalid_field_message}"
    )
    context["result"] = {
        "result_message": result_message,
        "result_message_details": result_message_details,
        "error": f"Form was invalid: {form_errors}",
    }
    return context


def get_urn_info(request):
    urn = request.GET.get("urn", None)
    context = {}
    if urn:
        instance = get_model_by_urn(urn)
        pmids = (
            [f"{pmid}" for pmid in instance.pubmed_ids.all()]
            if len(instance.pubmed_ids.all()) > 0
            else []
        )
        context["selected_urn"] = urn
        context["pmids"] = pmids
    return render(request, "manager/manage_addpmid_table.html", context)


def user_is_power(user):
    if not user.userrole.is_poweruser:
        raise PermissionDenied("Must be a power user to view this page.")
    return True


@login_required(login_url=reverse_lazy("accounts:login"))
@user_passes_test(user_is_power, redirect_field_name=None)
def manage_view(request):
    return render(request, "manager/manage.html", _default_context())


@login_required(login_url=reverse_lazy("accounts:login"))
@user_passes_test(user_is_power, redirect_field_name=None)
def manage_addpmid_view(request):
    context = _default_context()
    scoresets = ScoreSet.objects.all()
    context["urns"] = [s.urn for s in scoresets]
    if request.method == "POST":
        form = AddPmidForm(data=request.POST)
        if form.is_valid():
            urn = form.cleaned_data["urn"]
            pmid = form.cleaned_data["pmid"]
            try:
                call_command("addpmid", urn=urn, pmid=pmid)
                context["result"] = {
                    "result_message": "Successfully added PubMedID."
                }
            except CommandError as e:
                context["result"] = {
                    "result_message": "Error adding PMID.",
                    "result_message_details": e,
                    "error": e,
                }
        else:
            context = _update_context_with_invalid_errors(context, form.errors)
    return render(request, "manager/manage_addpmid.html", context)


@login_required(login_url=reverse_lazy("accounts:login"))
@user_passes_test(user_is_power, redirect_field_name=None)
def manage_adduser_view(request):
    context = _default_context()
    valid_states = (
        constants.administrator,
        constants.editor,
        constants.viewer,
    )
    scoresets = ScoreSet.objects.all()
    context["urns"] = [s.urn for s in scoresets]
    context["roles"] = [r for r in valid_states]
    users = User.objects.all()
    context["users"] = sorted(
        [
            (user.profile.get_short_name(), user.username)
            for user in users
            if not user.profile.is_anon()
        ]
    )
    if request.method == "POST":
        form = AddUserForm(data=request.POST)
        if form.is_valid():
            user_id = form.cleaned_data["user_id"]
            urn = form.cleaned_data["urn"]
            role = form.cleaned_data["role"]
            try:
                call_command("adduser", user=user_id, urn=urn, role=role)
                context["result"] = {
                    "result_message": "Successfully added user."
                }
            except CommandError as e:
                context["result"] = {
                    "result_message": "Error adding user.",
                    "result_message_details": e,
                    "error": e,
                }
        else:
            context = _update_context_with_invalid_errors(context, form.errors)
    return render(request, "manager/manage_adduser.html", context)


@login_required(login_url=reverse_lazy("accounts:login"))
@user_passes_test(user_is_power, redirect_field_name=None)
def manage_createnews_view(request):
    context = _default_context()
    context["levels"] = [i[0] for i in News.STATUS_CHOICES]
    if request.method == "POST":
        form = CreateNewsForm(data=request.POST)
        if form.is_valid():
            message = form.cleaned_data["message"]
            level = form.cleaned_data["level"]
            try:
                call_command("createnews", message=message, level=level)
                context["result"] = {
                    "result_message": "Successfully created news post."
                }
            except CommandError as e:
                context["result"] = {
                    "result_message": "Error creating news post.",
                    "result_message_details": e,
                    "error": e,
                }
        else:
            context = _update_context_with_invalid_errors(context, form.errors)

    return render(request, "manager/manage_createnews.html", context)


@login_required(login_url=reverse_lazy("accounts:login"))
@user_passes_test(user_is_power, redirect_field_name=None)
def manage_setuserrole_view(request):
    context = _default_context()
    context["roles"] = [i[0] for i in Role.choices()]
    users = User.objects.all()
    context["users"] = sorted(
        [
            (user.profile.get_short_name(), user.username)
            for user in users
            if not user.profile.is_anon()
        ]
    )
    if request.method == "POST":
        form = SetUserRoleForm(data=request.POST)
        if form.is_valid():
            user_id = form.cleaned_data["user_id"]
            role = form.cleaned_data["role"]
            try:
                call_command("setuserrole", user=user_id, role=role)
                context["result"] = {
                    "result_message": f"Successfully set user role to {role} for user {user_id}."
                }
            except CommandError as e:
                context["result"] = {
                    "result_message": "Error setting user role.",
                    "result_message_details": e,
                    "error": e,
                }
        else:
            context = _update_context_with_invalid_errors(context, form.errors)

    return render(request, "manager/manage_setuserrole.html", context)
