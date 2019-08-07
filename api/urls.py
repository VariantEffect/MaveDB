from rest_framework.routers import DefaultRouter
from django.conf.urls import url

from dataset.constants import scoreset_url_pattern

from . import views

router = DefaultRouter()
router.register("users", views.UserViewset)
router.register("experimentsets", views.ExperimentSetViewset)
router.register("experiments", views.ExperimentViewset)
router.register("scoresets", views.ScoreSetViewset)

router.register("keyword", views.KeywordViewSet)
router.register("pubmed", views.PubmedIdentifierViewSet)
router.register("doi", views.DoiIdentifierViewSet)
router.register("sra", views.SraIdentifierViewSet)
router.register("refseq", views.RefseqIdentifierViewSet)
router.register("uniprot", views.UniprotIdentifierViewSet)
router.register("ensembl", views.EnsemblIdentifierViewSet)
router.register("genome", views.GenomeIdentifierViewSet)
router.register("target", views.TargetGeneViewSet)
router.register("reference", views.ReferenceGenomeViewSet)

scoreset_urls = [
    url(
        r"^scoresets/(?P<urn>{})/scores/$".format(scoreset_url_pattern),
        views.scoreset_score_data,
        name="api_download_score_data",
    ),
    url(
        r"^scoresets/(?P<urn>{})/counts/$".format(scoreset_url_pattern),
        views.scoreset_count_data,
        name="api_download_count_data",
    ),
    url(
        r"^scoresets/(?P<urn>{})/metadata/$".format(scoreset_url_pattern),
        views.scoreset_metadata,
        name="api_download_metadata",
    ),
]


urlpatterns = router.urls + scoreset_urls
