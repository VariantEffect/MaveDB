import csv
from functools import reduce
from django.shortcuts import render
from django.db.models import Q
from django.contrib.auth import get_user_model

from accounts.permissions import user_is_anonymous
from accounts.forms import UserSearchForm
from accounts.mixins import UserFilterMixin

from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet
from dataset.mixins import ExperimentFilterMixin, ScoreSetFilterMixin
from .forms import (
    MetadataSearchForm,
    MetaIdentifiersSearchForm,
    TargetIdentifierSearchForm,
    GenomeSearchForm
)

User = get_user_model()

experiment_searher = ExperimentFilterMixin()
scoreset_searcher = ScoreSetFilterMixin()
user_searcher = UserFilterMixin()


def search_view(request):
    user_q = None
    user_search_form = UserSearchForm()
    meta_search_form = MetadataSearchForm()
    meta_id_search_form = MetaIdentifiersSearchForm()
    target_id_search_form = TargetIdentifierSearchForm()
    genome_search_form = GenomeSearchForm()
    experiments = Experiment.objects.all()
    scoresets = ScoreSet.objects.all()

    search_all = 'search' in request.GET

    if request.method == "GET" and request.GET:
        if search_all:
            try:
                parsed_list = list(csv.reader(
                    [v.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
                     for v in request.GET.getlist('search', [])]
                ))
                flattened = []
                for sublist in parsed_list:
                    if isinstance(sublist, list):
                        flattened.extend(sublist)
                if flattened:
                    exp_q = experiment_searher.search_all(
                        flattened, join_func=experiment_searher.or_join_qs)
                    scs_q = scoreset_searcher.search_all(
                        flattened, join_func=experiment_searher.or_join_qs)
                    user_q = user_searcher.search_all(
                        flattened, join_func=experiment_searher.or_join_qs)
                else:
                    exp_q = Q()
                    scs_q = Q()
                    user_q = Q()
            except (ValueError, TypeError):
                exp_q = None
                scs_q = None
                user_q = None
        else:
            user_search_form = UserSearchForm(request.GET)
            meta_search_form = MetadataSearchForm(request.GET)
            meta_id_search_form = MetaIdentifiersSearchForm(request.GET)
            target_id_search_form = TargetIdentifierSearchForm(request.GET)
            genome_search_form = GenomeSearchForm(request.GET)

            exp_qs = []
            scs_qs = []

            # MetadataSearchForm
            if meta_search_form.is_valid():
                exp_qs.extend(
                    meta_search_form.make_experiment_filters(join=False))
                scs_qs.extend(
                    meta_search_form.make_scoreset_filters(join=False))

            # MetaIdentifiersSearchForm
            if meta_id_search_form.is_valid():
                exp_qs.extend(
                    meta_id_search_form.make_experiment_filters(join=False))
                scs_qs.extend(
                    meta_id_search_form.make_scoreset_filters(join=False))

            # TargetIdentifierSearchForm
            if target_id_search_form.is_valid():
                exp_qs.extend(
                    target_id_search_form.make_experiment_filters(join=False))
                scs_qs.extend(
                    target_id_search_form.make_scoreset_filters(join=False))

            # GenomeSearchForm
            if genome_search_form.is_valid():
                exp_qs.extend(
                    genome_search_form.make_experiment_filters(join=False))
                scs_qs.extend(
                    genome_search_form.make_scoreset_filters(join=False))

            if user_search_form.is_valid():
                user_q = user_search_form.make_filters(join=True)

            if search_all:
                exp_q = experiment_searher.or_join_qs(exp_qs)
                scs_q = scoreset_searcher.or_join_qs(scs_qs)
            else:
                exp_q = experiment_searher.and_join_qs(exp_qs)
                scs_q = scoreset_searcher.and_join_qs(scs_qs)

        if scs_q is None and exp_q is None and user_q is None:
            # Error occurred during CSV parsing.
            experiments = Experiment.objects.none()
            scoresets = ScoreSet.objects.none()
        else:
            if len(exp_q):
                experiments = experiments.filter(exp_q).distinct()
            if len(scs_q):
                scoresets = scoresets.filter(scs_q).distinct()
            if len(user_q):
                users = User.objects.filter(user_q).distinct()
                user_experiments = [
                    u.profile.contributor_experiments()
                    for u in users if not user_is_anonymous(u)
                ]
                user_scoresets = [
                    u.profile.contributor_scoresets()
                    for u in users if not user_is_anonymous(u)
                ]
                user_experiments = reduce(
                    lambda x, y: x.union(y),
                    user_experiments,
                    Experiment.objects.none()
                )
                user_scoresets = reduce(
                    lambda x, y: x.union(y),
                    user_scoresets,
                    ScoreSet.objects.none()
                )
                if not search_all:
                    experiments = experiments.intersection(user_experiments)
                    scoresets = scoresets.intersection(user_scoresets)
                else:
                    experiments = experiments.union(user_experiments)
                    scoresets = scoresets.union(user_scoresets)

    instances = list(scoresets.distinct()) + list(experiments.distinct())
    context = {
        "meta_search_form": meta_search_form,
        "meta_id_search_form": meta_id_search_form,
        "target_id_search_form": target_id_search_form,
        "genome_search_form": genome_search_form,
        "user_search_form": user_search_form,
        "instances": instances,
    }

    return render(request, "search/search.html", context)
