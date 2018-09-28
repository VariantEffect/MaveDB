from rest_framework.routers import DefaultRouter
from django.conf.urls import url

from accounts.models import AUTH_TOKEN
from dataset.constants import scoreset_url_pattern

from . import views

router = DefaultRouter()
router.register('users', views.UserViewset)
router.register('experimentsets', views.ExperimentSetViewset)
router.register('experiments', views.ExperimentViewset)
router.register('scoresets', views.ScoreSetViewset)

experimentset_list = views.ExperimentSetViewset.as_view({'get': 'list'})
experimentset_detail = views.ExperimentSetViewset.as_view({'get': 'retrieve'})

experiment_list = views.ExperimentViewset.as_view({'get': 'list'})
experiment_detail = views.ExperimentViewset.as_view({'get': 'retrieve'})

scoreset_list = views.ScoreSetViewset.as_view({'get': 'list'})
scoreset_detail = views.ScoreSetViewset.as_view({'get': 'retrieve'})

user_list = views.UserViewset.as_view({'get': 'list'})
user_detail = views.UserViewset.as_view({'get': 'retrieve'})



scoreset_urls = [
    url(
        r"^scoresets/(?P<urn>{})/scores/$".format(
            scoreset_url_pattern),
        views.scoreset_score_data,
        name="api_download_score_data"
    ),
    url(
        r"^scoresets/(?P<urn>{})/counts/$".format(
            scoreset_url_pattern),
        views.scoreset_count_data,
        name="api_download_count_data"
    ),
    url(
        r"^scoresets/(?P<urn>{})/metadata/$".format(
            scoreset_url_pattern),
        views.scoreset_metadata,
        name="api_download_metadata"
    )
]


urlpatterns = router.urls + scoreset_urls
