"""
Views for accounts app.
"""

from django.core.mail import send_mail
from django.core.exceptions import ValidationError

from django.shortcuts import render, reverse, redirect

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site

from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string

from .tokens import account_activation_token
from .forms import RegistrationForm


@login_required
def profile_view(request):
    context = {}
    return render(request, 'accounts/profile.html', context)


def activate_account_view(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, 'accounts/activation_valid.html')
    else:
        if user is not None:
            user.delete()
        return render(request, 'accounts/activation_invalid.html')


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
                use_https = request.is_secure()
                subject = 'Activate Your Account'
                message = render_to_string(
                    'accounts/activation_email.html', {
                        'user': user,
                        'protocol': 'https' if use_https else 'http',
                        'domain': get_current_site(request).domain,
                        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                        'token': account_activation_token.make_token(user)})
                user.email_user(subject, message)
                return render(request, 'accounts/registration_success.html')

    context = {'form': form}
    return render(request, 'accounts/register.html', context)
