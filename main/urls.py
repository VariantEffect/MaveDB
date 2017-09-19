
"""
Url patterns for the main database app.
"""

from django.conf.urls import url, include

from .views import home_view
from .views import documentation_view
from .views import terms_privacy_view, help_contact_view

urlpatterns = [
    url(r'^$', home_view, name='home'),
    url(r'docs/$', documentation_view, name='documentation'),
    url(r'contact/$', help_contact_view, name='contact'),
    url(r'terms_privacy/$', terms_privacy_view, name='terms_privacy'),
]
