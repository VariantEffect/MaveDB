
"""
Url patterns for the experiment database app.
"""
from functools import partial

from django.conf.urls import url

from .constants import (
    experiment_url_pattern,
    experimentset_url_pattern,
    scoreset_url_pattern,
    variant_score_data, variant_count_data
)
from .views import (
    ExperimentDetailView, ExperimentSetDetailView, ScoreSetDetailView,
    experiment_create_view, scoreset_create_view, download_scoreset_data
)

download_scores = partial(download_scoreset_data, dataset_key=variant_score_data)
download_counts = partial(download_scoreset_data, dataset_key=variant_count_data)

urlpatterns = [
    url(
        r'(?P<urn>{})'.format(scoreset_url_pattern),
        ScoreSetDetailView.as_view(), name='scoreset_detail'
    ),
    url(
        r'(?P<urn>{})'.format(experiment_url_pattern),
        ExperimentDetailView.as_view(), name='experiment_detail'
    ),
    url(
        r'(?P<urn>{})'.format(experimentset_url_pattern),
        ExperimentSetDetailView.as_view(), name='experimentset_detail'
    ),
    url(
        r'new/$', experiment_create_view, name='experiment_new'
    ),
    url(
        r'new/$', scoreset_create_view, name='scoreset_new'
    ),
    url(
        r'(?P<urn>{})'.format(scoreset_url_pattern),
        download_scores, name='scores_download'
    ),
    url(
        r'(?P<urn>{})'.format(scoreset_url_pattern),
        download_counts, name='counts_download'
    ),

]
