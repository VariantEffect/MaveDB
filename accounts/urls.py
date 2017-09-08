"""
mavedb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/

Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')

Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')

Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

from django.conf.urls import url, include
from django.urls import reverse_lazy
import django.contrib.auth.views as auth_views

from .views import registration_view, profile_view
from .views import activate_account_view, send_activation_email_view
from .views import manage_instance, edit_instance, view_instance
from .views import login_with_remember_me


urlpatterns = [
    # ------ Register
    url(r"register/$", registration_view, name="register"),
    url(r"activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$",
        activate_account_view, name="activate"),
    url(r"activate/(?P<uidb64>[0-9A-Za-z_\-]+)/$",
        send_activation_email_view, name='send_activation_email'),

    # ------ Login and Logout
    url(
        r'login/$',
        login_with_remember_me,
        name='login'),
    url(
        r'logout/$',
        auth_views.LogoutView.as_view(),
        name='logout'),

    # ------ Password Resetting
    url(
        r'password_reset/$',
        auth_views.PasswordResetView.as_view(
            success_url=reverse_lazy("accounts:password_reset_done")),
        name='password_reset'),
    url(
        r'password_reset/done/$',
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done"),
    url(
        r'reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.PasswordResetConfirmView.as_view(
            success_url=reverse_lazy("accounts:password_reset_complete")),
        name="password_reset_confirm"),
    url(
        r'reset/done/$',
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete"),

    # ------ Profile
    url(r"^$", profile_view, name="index"),
    url(r"profile/$", profile_view, name="profile"),
    url(
        r"profile/manage/(?P<accession>[A-Za-z]{3,4}\d+.*)/$",
        manage_instance,
        name="manage_instance"
    ),
    url(
        r"profile/edit/(?P<accession>[A-Za-z]{3,4}\d+.*)/$",
        edit_instance,
        name="edit_instance"
    ),
    url(
        r"profile/view/(?P<accession>[A-Za-z]{3,4}\d+.*)/$",
        view_instance,
        name="view_instance"
    )
]
