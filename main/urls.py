
"""
Url patterns for the main database app.
"""

from django.conf.urls import url

from .views import home_view, search_view
from .views import basic_search_view, advanced_search_view
from .views import experiment_detail_view, scoreset_detail_view

from .views import download_view, upload_view, login_register_view
from .views import usage_guide_view, documentation_view
from .views import terms_privacy_view, help_contact_view

from .views import new_experiment_view, new_scoreset_view

urlpatterns = [
    url(r'^$', home_view, name='home'),

    url(r'download/$', download_view, name='download'),
    url(r'upload/$', upload_view, name='upload'),

    url(r'usageguide/$', usage_guide_view, name='usage_guide'),
    url(r'documentation/$', documentation_view, name='documentation'),
    url(r'login/$', login_register_view, name='login'),
    url(r'register/$', login_register_view, name='register'),
    url(r'contact/$', help_contact_view, name='contact'),
    url(r'help/$', help_contact_view, name='help'),
    url(r'terms/$', terms_privacy_view, name='terms'),
    url(r'privacy/$', terms_privacy_view, name='privacy'),

    url(r'search/$', search_view, name='search'),
    url(r'search/basic/$', basic_search_view, name='basic_search'),
    url(r'search/advanced/$', advanced_search_view, name='advanced_search'),

    url(r'experiment/((EXP|exp)\d+\w+)/(?P<accession>(SCS|scs)\w+.\d+)/$',
        scoreset_detail_view, name='scoreset_detail'),
    url(r'scoreset/new/$', new_scoreset_view, name="new_scoreset"),

    url(r'experiment/(?P<accession>(EXP|exp)\d+\w+)/$',
        experiment_detail_view, name='experiment_detail'),
    url(r'experiment/new/$', new_experiment_view, name="new_experiment")
]
