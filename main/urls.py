"""
Url patterns for the main database app.
"""

from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.home_view, name='home'),
    url(r'docs/$', views.documentation_view, name='documentation'),
    url(r'contact/$', views.help_contact_view, name='contact'),
    url(r'terms_privacy/$', views.terms_privacy_view, name='terms_privacy'),
    url(r'^robots.txt$', views.robots, name='robots')
]
