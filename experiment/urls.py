
"""
Url patterns for the experiment database app.
"""

from django.conf.urls import url, include

from .views import (
    ExperimentDetailView, ExperimentSetDetailView,
    ExperimentCreateView
)

urlpatterns = [
    url(
        r'(?P<accession>(EXP|exp)\d{6}[A-Z]+)/$',
        ExperimentDetailView.as_view(), name='experiment_detail'
    ),
    url(
        r'(?P<accession>(EXPS|exp)\d{6})/$',
        ExperimentSetDetailView.as_view(), name='experimentset_detail'
    ),
    url(
        r'new/$',
        ExperimentCreateView.as_view(), name='experiment_new'
    ),
]
