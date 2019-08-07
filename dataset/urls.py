"""
Url patterns for the experiment database app.
"""
from django.conf.urls import url

from api.views import (
    scoreset_metadata,
    scoreset_count_data,
    scoreset_score_data,
)

from .constants import (
    experiment_url_pattern,
    experimentset_url_pattern,
    scoreset_url_pattern,
)

from .views.experimentset import ExperimentSetDetailView
from .views.experiment import ExperimentDetailView, ExperimentCreateView
from .views.scoreset import ScoreSetDetailView, ScoreSetCreateView


urlpatterns = [
    url(
        r"^scoreset/(?P<urn>{})/$".format(scoreset_url_pattern),
        ScoreSetDetailView.as_view(),
        name="scoreset_detail",
    ),
    url(
        r"^experiment/(?P<urn>{})/$".format(experiment_url_pattern),
        ExperimentDetailView.as_view(),
        name="experiment_detail",
    ),
    url(
        r"^experimentset/(?P<urn>{})/$".format(experimentset_url_pattern),
        ExperimentSetDetailView.as_view(),
        name="experimentset_detail",
    ),
    url(
        r"^experiment/new/$",
        ExperimentCreateView.as_view(),
        name="experiment_new",
    ),
    url(r"^scoreset/new/$", ScoreSetCreateView.as_view(), name="scoreset_new"),
    url(
        r"^scoreset/(?P<urn>{})/scores/$".format(scoreset_url_pattern),
        scoreset_score_data,
        name="scores_download",
    ),
    url(
        r"^scoreset/(?P<urn>{})/counts/$".format(scoreset_url_pattern),
        scoreset_count_data,
        name="counts_download",
    ),
    url(
        r"^scoreset/(?P<urn>{})/metadata/$".format(scoreset_url_pattern),
        scoreset_metadata,
        name="metadata_download",
    ),
]
