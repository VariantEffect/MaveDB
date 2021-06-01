"""
Url patterns for the main database app.
"""

from django.conf.urls import url
from django.conf import settings
from django.views.static import serve

from . import views

urlpatterns = [
    url(r"^$", views.home_view, name="home"),
    # ------------ MaveHGVS documentation ---------------------- #
    url(
        r"^docs/mavedb/$",
        serve,
        {
            "document_root": settings.MAVEDB_DOCS_ROOT,
            "path": "index.html",
        },
        name="mavedb-documentation",
    ),
    url(
        r"^docs/mavedb/(?P<path>.*)$",
        serve,
        {"document_root": settings.MAVEDB_DOCS_ROOT},
        name="mavedb-documentation-with-path",
    ),
    # ------------ MaveHGVS documentation ---------------------- #
    url(
        r"^docs/mavehgvs/$",
        serve,
        {
            "document_root": settings.MAVEHGVS_DOCS_ROOT,
            "path": "index.html",
        },
        name="mavehgvs-documentation",
    ),
    url(
        r"^docs/mavehgvs/(?P<path>.*)$",
        serve,
        {"document_root": settings.MAVEHGVS_DOCS_ROOT},
        name="mavehgvs-documentation-with-path",
    ),
    url(r"^contact/$", views.help_contact_view, name="contact"),
    url(r"^terms_privacy/$", views.terms_privacy_view, name="terms_privacy"),
    url(r"^robots.txt/$", views.robots, name="robots"),
]
