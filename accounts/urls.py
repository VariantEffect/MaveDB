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

from dataset.constants import (
    scoreset_url_pattern, experiment_url_pattern, any_url_pattern
)

from .views import registration_view, profile_view, log_user_out, login_error
from .views import manage_instance, login_delegator

from dataset.views.experiment import ExperimentEditView
from dataset.views.scoreset import ScoreSetEditView


urlpatterns = [
    # ------ Register
    url(r"register/$", registration_view, name="register"),

    # ------ Social stuff
    url(r"profile/error/$", login_error, name="login_error"),
    url(
        r'^oauth/', include('social_django.urls', namespace='social'),
        name="social"
    ),

    # ------ Login and Logout
    url(r'^logout/$', log_user_out, name='logout'),
    url(r'login/$', login_delegator, name='login'),

    # ------ Profile
    url(r"profile/$", profile_view, name="profile"),
    url(
        r"profile/manage/(?P<urn>{})/$".format(any_url_pattern),
        manage_instance,
        name="manage_instance"
    ),
    url(
        r"profile/edit/experiment/(?P<urn>{})/$".format(experiment_url_pattern),
        ExperimentEditView.as_view(),
        name="edit_experiment"
    ),
    url(
        r"profile/edit/scoreset/(?P<urn>{})/$".format(scoreset_url_pattern),
        ScoreSetEditView.as_view(),
        name="edit_scoreset"
    ),
]
