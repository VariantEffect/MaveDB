
"""
Url patterns for the experiment database app.
"""

from django.conf.urls import url, include

from .views import (
    ScoresetDetailView, scoreset_create_view,
    download_scoreset_data, download_scoreset_metadata
)

urlpatterns = [
    url(
        r'(?P<accession>(SCS|scs)\d{6}[A-Z]+.\d+)/$',
        ScoresetDetailView.as_view(), name='scoreset_detail'
    ),
    url(
        r'(?P<accession>(SCS|scs)\d{6}[A-Z]+.\d+)/(?P<dataset_key>(scores|counts))/$',
        download_scoreset_data, name='scoreset_download'
    ),
    url(
        r'(?P<accession>(SCS|scs)\d{6}[A-Z]+.\d+)/metadata/$',
        download_scoreset_metadata, name='scoreset_metadata'
    ),
    url(
        r'new/$',
        scoreset_create_view, name='scoreset_new'
    ),
]
