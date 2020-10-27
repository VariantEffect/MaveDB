"""
Url patterns for the main database app.
"""

from django.conf.urls import url
from django.conf import settings
from django.views.static import serve

from . import views

urlpatterns = [
    url(r"^$", views.home_view, name="home"),
    # url(r"^docs/$", views.documentation_view, name="documentation"),
    url(
        r"^docs/$",
        serve,
        {
            "document_root": settings.DOCS_ROOT,
            "path": "index.html",
        },
        name="documentation",
    ),
    url(
        r"^docs/(?P<path>.*)$",
        serve,
        {"document_root": settings.DOCS_ROOT},
        name="documentation-with-path",
    ),
    url(r"^contact/$", views.help_contact_view, name="contact"),
    url(r"^terms_privacy/$", views.terms_privacy_view, name="terms_privacy"),
    url(r"^robots.txt/$", views.robots, name="robots"),
]
