from rest_framework.routers import DefaultRouter
from django.conf.urls import url


from dataset.constants import (
    scoreset_url_pattern, experiment_url_pattern,
    experimentset_url_pattern
)

from .views import (
    UserViewset,
    ExperimentViewset, ExperimentSetViewset, ScoreSetViewset, UserViewset,
    scoreset_count_data, scoreset_score_data, scoreset_metadata
)

router = DefaultRouter()
router.register('users', UserViewset)
router.register('experimentsets', ExperimentSetViewset, base_name='list')
router.register('experiments', ExperimentViewset, base_name='list')
router.register('scoresets', ScoreSetViewset)

experimentset_list = ExperimentSetViewset.as_view({'get': 'list'})
experimentset_detail = ExperimentSetViewset.as_view({'get': 'retrieve'})

experiment_list = ExperimentViewset.as_view({'get': 'list'})
experiment_detail = ExperimentViewset.as_view({'get': 'retrieve'})

scoreset_list = ScoreSetViewset.as_view({'get': 'list'})
scoreset_detail = ScoreSetViewset.as_view({'get': 'retrieve'})

user_list = UserViewset.as_view({'get': 'list'})
user_detail = UserViewset.as_view({'get': 'retrieve'})


experimentset_urls = [
    url(
        r"experimentsets/$", experimentset_list, name="experimentset_list"
    ),
    url(
        r"(?P<urn>{})/$".format(experimentset_url_pattern),
        experimentset_detail,
        name="experimentset_detail"
    ),
]

experiment_urls = [
    url(
        r"experiments/$", experiment_list, name="experiment_list"
    ),
    url(
        r"(?P<urn>{})/$".format(experiment_url_pattern),
        experiment_detail,
        name="experiment_detail"
    ),
]

scoreset_urls = [
    url(
        r"scoresets/$", scoreset_list, name="scoreset_list"
    ),
    url(
        r"(?P<urn>{})/$".format(scoreset_url_pattern),
        scoreset_detail,
        name="scoreset_detail"
    ),
    url(
        r"(?P<urn>{})/scores/$".format(scoreset_url_pattern),
        scoreset_score_data,
        name="api_download_score_data"
    ),
    url(
        r"(?P<urn>{})/counts/$".format(scoreset_url_pattern),
        scoreset_count_data,
        name="api_download_count_data"
    ),
    url(
        r"(?P<urn>{})/metadata/$".format(scoreset_url_pattern),
        scoreset_metadata,
        name="api_download_metadata"
    )
]


urlpatterns = router.urls + experimentset_urls + experiment_urls + scoreset_urls
