
"""
Url patterns for the experiment database app.
"""

from django.conf.urls import url, include

from .views import (
    ExperimentDetailView, ExperimentSetDetailView,
    experiment_create_view
)

urlpatterns = [
    url(
        r'(?P<urn>(EXP|exp)\d{6}[A-Z]+)/$',
        ExperimentDetailView.as_view(), name='experiment_detail'
    ),
    url(
        r'(?P<urn>(EXPS|exp)\d{6})/$',
        ExperimentSetDetailView.as_view(), name='experimentset_detail'
    ),
    url(
        r'new/$',
        experiment_create_view, name='experiment_new'
    ),
]
