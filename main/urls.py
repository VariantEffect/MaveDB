
"""
Url patterns for the main database app.
"""

from django.conf.urls import url

from .views import home_view, search_view

urlpatterns = [
    url(r'^$', home_view, name='home'),
    url(r'search/?$', search_view, name='search'),
]