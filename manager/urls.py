"""
Url patterns for the admin app.
"""

from django.conf.urls import url
from django.conf import settings
from django.views.static import serve

from . import views

urlpatterns = [
    url(r"^$", views.manage_view, name="manage"),
    url(r"^get_urn_info/$", views.get_urn_info, name="get_urn_info"),
    url(r"^addpmid/$", views.manage_addpmid_view, name="manage_addpmid"),
    url(r"^adduser/$", views.manage_adduser_view, name="manage_adduser"),
    url(
        r"^createnews/$",
        views.manage_createnews_view,
        name="manage_createnews",
    ),
    url(
        r"^setuserrole/$",
        views.manage_setuserrole_view,
        name="manage_setuserrole",
    ),
]
