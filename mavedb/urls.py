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
from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin

import core.views


handler403 = "main.views.handler403"
handler404 = "main.views.handler404"
handler500 = "main.views.handler500"

urlpatterns = [
    url("^", include("social_django.urls", namespace="social")),
    url(r"^", include("main.urls", namespace="main"), name="main"),
    url(r"^api/", include("api.urls", namespace="api"), name="api"),
    url(r"^", include("accounts.urls", namespace="accounts"), name="accounts"),
    url(r"^", include("dataset.urls", namespace="dataset"), name="dataset"),
    url(
        r"^manage/",
        include("manager.urls", namespace="manager"),
        name="manage",
    ),
    url(
        r"^search/", include("search.urls", namespace="search"), name="search"
    ),
    # ----- Admin
    url(r"^admin/stats/$", core.views.get_pageview_stats, name="page-stats"),
]

if settings.ADMIN_ENABLED:
    urlpatterns += [
        url(r"^admin/", admin.site.urls),
        url(r"^tracking/", include("tracking.urls")),
    ]
