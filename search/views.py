import csv
from functools import reduce
from django.shortcuts import render
from django.contrib.auth import get_user_model

from accounts.permissions import user_is_anonymous
from accounts.forms import UserSearchForm
from accounts.mixins import UserSearchMixin

from dataset.models.experiment import Experiment
from dataset.mixins import ExperimentSearchMixin
from .forms import (
    MetadataSearchForm,
    MetaIdentifiersSearchForm,
    TargetIdentifierSearchForm,
    GenomeSearchForm
)

User = get_user_model()

searher = ExperimentSearchMixin()
user_searcher = UserSearchMixin()


def search_view(request):
    user_q = None
    user_search_form = UserSearchForm(request.GET)
    meta_search_form = MetadataSearchForm()
    meta_id_search_form = MetaIdentifiersSearchForm()
    target_id_search_form = TargetIdentifierSearchForm()
    genome_search_form = GenomeSearchForm()
    experiments = Experiment.objects.all()

    search_all = bool(request.GET.get('search', ""))

    if request.method == "GET" and request.GET:
        if search_all:
            try:
                v_list = list(csv.reader(
                    [v.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
                     for v in request.GET.getlist('search', [])]
                ))
                v_list = [sl[0] for sl in v_list]
                q = searher.search_all(v_list, join_func=searher.or_join_qs)
                user_q = user_searcher.search_all(
                    v_list, join_func=searher.or_join_qs)
            except (ValueError, TypeError):
                q = None
                user_q = None
        else:
            user_search_form = UserSearchForm(request.GET)
            meta_search_form = MetadataSearchForm(request.GET)
            meta_id_search_form = MetaIdentifiersSearchForm(request.GET)
            target_id_search_form = TargetIdentifierSearchForm(request.GET)
            genome_search_form = GenomeSearchForm(request.GET)

            qs = []
            if meta_search_form.is_valid():
                qs.extend(meta_search_form.make_filters(join=False))
            if meta_id_search_form.is_valid():
                qs.extend(meta_id_search_form.make_filters(join=False))
            if target_id_search_form.is_valid():
                qs.extend(target_id_search_form.make_filters(join=False))
            if genome_search_form.is_valid():
                qs.extend(genome_search_form.make_filters(join=False))
            if user_search_form.is_valid():
                user_q = user_search_form.make_filters(join=True)

            if search_all:
                q = searher.or_join_qs(qs)
            else:
                q = searher.and_join_qs(qs)

        if q is None or user_q is None:
            # Invalid query causing a CSV reader error.
            experiments = Experiment.objects.none()
        else:
            experiments = experiments.filter(q).distinct()
            if user_q:
                users = User.objects.filter(user_q).distinct()
                user_experiments = [
                    u.profile.contributor_experiments()
                    for u in users if not user_is_anonymous(u)
                ]
                user_experiments = reduce(
                    lambda x, y: x.union(y), user_experiments
                )
                if not search_all:
                    experiments = experiments.intersection(user_experiments)
                else:
                    experiments = experiments.union(user_experiments)
    context = {
        "meta_search_form": meta_search_form,
        "meta_id_search_form": meta_id_search_form,
        "target_id_search_form": target_id_search_form,
        "genome_search_form": genome_search_form,
        "user_search_form": user_search_form,
        "experiments": experiments,
    }

    return render(request, "search/search.html", context)
