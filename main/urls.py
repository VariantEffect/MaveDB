
"""
Url patterns for the main database app.
"""

from django.conf.urls import url

from .views import home_view

urlpatterns = [
    url(r'', home_view, name='home')
]