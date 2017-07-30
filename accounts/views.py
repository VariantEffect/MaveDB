"""
Views for accounts app.
"""

from django.core.mail import send_mail
from django.core.exceptions import ValidationError

from django.shortcuts import render, reverse, redirect

from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site

from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode

from .tokens import account_activation_token
from .forms import RegistrationForm, send_user_activation_email


@login_required
def profile_view(request):
    context = {}
    return render(request, 'accounts/profile.html', context)


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
