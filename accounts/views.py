"""
Views for accounts app.
"""

from django.apps import apps
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render, reverse, redirect

from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site

from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode

from guardian.shortcuts import get_objects_for_user

from .models import (
    user_is_admin_for_instance,
    user_is_contributor_for_instance,
    user_is_viewer_for_instance
)

from .tokens import account_activation_token
from .forms import RegistrationForm, send_user_activation_email


ExperimentSet = apps.get_model('experiment', 'ExperimentSet')
Experiment = apps.get_model('experiment', 'Experiment')
ScoreSet = apps.get_model('scoreset', 'ScoreSet')


@login_required(login_url=reverse_lazy("accounts:login"))
def profile_view(request):
    context = {}
    admin_models = []
    contrib_models = []
    viewer_models = []

    user = request.user
    experimentsets = get_objects_for_user(
        user, perms=[], any_perm=False, klass=ExperimentSet)
    experiments = get_objects_for_user(
        user, perms=[], any_perm=False, klass=Experiment)
    scoresets = get_objects_for_user(
        user, perms=[], any_perm=False, klass=ScoreSet)

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

    context = {
        "user": user,
        "experimentsets": experimentsets,
        "experiments": experiments,
        "scoresets": scoresets,
        "administrator_models": admin_models,
        "contributor_models": contrib_models,
        "viewer_models": viewer_models
    }

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
