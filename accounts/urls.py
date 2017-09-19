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

from .views import registration_view, profile_view, log_user_out, login_error
from .views import manage_instance, edit_instance, view_instance
from .views import login_delegator, list_all_users_and_their_data


urlpatterns = [
    # --- User list
    url(r"list/$", list_all_users_and_their_data, name="list_accounts"),

    # ------ Register
    url(r"register/$", registration_view, name="register"),

    # ------ Social stuff
    url(r"error", login_error, name="login_error"),
    url(
        r'^oauth/', include('social_django.urls', namespace='social'),
        name="social"
    ),

    # ------ Login and Logout
    url(r'^logout/$', log_user_out, name='logout'),
    url(
        r'login/$',
        login_delegator,
        name='login'
    ),

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
