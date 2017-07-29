
"""
Url patterns for the main database app.
"""

from django.conf.urls import url, include

from .views import home_view
from .views import download_view, upload_view
from .views import login_view, register_view
from .views import usage_guide_view, documentation_view
from .views import terms_privacy_view, help_contact_view

urlpatterns = [
    url(r'^$', home_view, name='home'),
    url(r'download/$', download_view, name='download'),
    url(r'upload/$', upload_view, name='upload'),
    url(r'usage/$', usage_guide_view, name='usage_guide'),
    url(r'docs/$', documentation_view, name='documentation'),
    url(r'contact/$', help_contact_view, name='contact'),
    url(r'help/$', help_contact_view, name='help'),
    url(r'terms_privacy/$', terms_privacy_view, name='terms_privacy'),
]
