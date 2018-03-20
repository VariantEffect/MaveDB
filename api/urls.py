from django.conf.urls import url, include


from .views import (
    users_all, user_by_username,
    experimentset_all, experimentset_by_urn,
    experiments_all, experiment_by_urn,
    scoresets_all, scoreset_by_urn,
    scoreset_count_data, scoreset_score_data
)

urlpatterns = [
    url(r"get/user/all/$", users_all, name="serialize_all_users"),
    url(
        r"get/user/(?P<username>.+)/$", user_by_username,
        name="serialize_user"
    ),

    # --- #
    url(
        r"get/experimentset/all/$", experimentset_all,
        name="serialize_all_experimentsets"
    ),
    url(
        r"get/experimentset/(?P<urn>(EXPS|exp)\d{6})/$",
        experimentset_by_urn,
        name="serialize_experimentset"
    ),

    # --- #
    url(
        r"get/experiment/all/$", experiments_all,
        name="serialize_all_experiments"
    ),
    url(
        r"get/experiment/(?P<urn>(EXP|exp)\d{6}[A-Z]+)/$",
        experiment_by_urn,
        name="serialize_experiment"
    ),

    # --- #
    url(r"get/scoreset/all/$", scoresets_all, name="serialize_all_scoresets"),
    url(
        r"get/scoreset/(?P<urn>(SCS|scs)\d{6}[A-Z]+.\d+)/$",
        scoreset_by_urn,
        name="serialize_scoreset"
    ),
    url(
        r"get/scoreset/(?P<urn>(SCS|scs)\d{6}[A-Z]+.\d+)/scores/$",
        scoreset_score_data,
        name="api_download_score_data"
    ),
    url(
        r"get/scoreset/(?P<urn>(SCS|scs)\d{6}[A-Z]+.\d+)/counts/$",
        scoreset_count_data,
        name="api_download_count_data"
    )
]
