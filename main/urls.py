
"""
Url patterns for the main database app.
"""

from django.conf.urls import url

from .views import home_view, search_view
from .views import basic_search_view, advanced_search_view

urlpatterns = [
    url(r'^$', home_view, name='home'),
    url(r'search/$', search_view, name='search'),
    url(r'search/basic/$', basic_search_view, name='basic_search'),
    url(r'search/advanced/$', advanced_search_view, name='advanced_search'),
]