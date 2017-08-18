
"""
Url patterns for the experiment database app.
"""

from functools import partial
from django.conf.urls import url, include

from .views import (
    ScoresetDetailView, scoreset_create_view,
    download_scoreset_data, download_scoreset_metadata
)

download_scores = partial(download_scoreset_data, dataset_key='scores')
download_counts = partial(download_scoreset_data, dataset_key='counts')

urlpatterns = [
    url(
        r'(?P<accession>(SCS|scs)\d{6}[A-Z]+.\d+)/$',
        ScoresetDetailView.as_view(), name='scoreset_detail'
    ),
    url(
        r'(?P<accession>(SCS|scs)\d{6}[A-Z]+.\d+)/scores/$',
        download_scores, name='scores_download'
    ),
    url(
        r'(?P<accession>(SCS|scs)\d{6}[A-Z]+.\d+)/counts/$',
        download_counts, name='counts_download'
    ),
    url(
        r'(?P<accession>(SCS|scs)\d{6}[A-Z]+.\d+)/metadata/$',
        download_scoreset_metadata, name='metadata_download'
    ),
    url(
        r'new/$',
        scoreset_create_view, name='scoreset_new'
    ),
]
