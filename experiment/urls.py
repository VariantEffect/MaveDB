
"""
Url patterns for the experiment database app.
"""

from django.conf.urls import url, include

from .views import ExperimentDetailView

urlpatterns = [
    url(
        r'(?P<accession>(EXP|exp)\d{6}[A-Z]+)/$',
        ExperimentDetailView.as_view(), name='experiment_detail'
    ),
]
