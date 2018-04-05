
"""
Url patterns for the experiment database app.
"""
from functools import partial

from django.conf.urls import url

from .constants import (
    experiment_url_pattern,
    experimentset_url_pattern,
    scoreset_url_pattern,
    variant_score_data,
    variant_count_data,
    variant_metadata
)

from .views.experimentset import ExperimentSetDetailView
from .views.experiment import ExperimentDetailView, experiment_create_view
from .views.scoreset import (
    ScoreSetDetailView, scoreset_create_view, download_scoreset_data
)

download_scores = partial(
    download_scoreset_data,
    dataset_key=variant_score_data
)
download_counts = partial(
    download_scoreset_data,
    dataset_key=variant_count_data
)
download_metadata = partial(
    download_scoreset_data,
    dataset_key=variant_metadata
)

urlpatterns = [
    url(
        r'scoreset/(?P<urn>{})/$'.format(scoreset_url_pattern),
        ScoreSetDetailView.as_view(), name='scoreset_detail'
    ),
    url(
        r'experiment/(?P<urn>{})/$'.format(experiment_url_pattern),
        ExperimentDetailView.as_view(), name='experiment_detail'
    ),
    url(
        r'experimentset/(?P<urn>{})/$'.format(experimentset_url_pattern),
        ExperimentSetDetailView.as_view(), name='experimentset_detail'
    ),
    url(
        r'experiment/new/$', experiment_create_view, name='experiment_new'
    ),
    url(
        r'scoreset/new/$', scoreset_create_view, name='scoreset_new'
    ),
    url(
        r'scoreset/(?P<urn>{})/score_data/$'.format(scoreset_url_pattern),
        download_scores, name='scores_download'
    ),
    url(
        r'scoreset/(?P<urn>{})/count_data/$'.format(scoreset_url_pattern),
        download_counts, name='counts_download'
    ),
    url(
        r'scoreset/(?P<urn>{})/metadata/$'.format(scoreset_url_pattern),
        download_metadata, name='metadata_download'
    )
]
