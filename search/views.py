from typing import Dict, List, Union, Tuple, Optional
from collections import Counter
import math

from django.db.models import QuerySet
from django.forms import Form
from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.http.response import JsonResponse
from django.core.paginator import Paginator, Page

from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet
from dataset.templatetags.dataset_tags import (
    format_urn_name_for_user,
    display_targets,
    filter_visible,
)
from dataset.filters import ScoreSetFilter, ExperimentFilter

from . import forms

User = get_user_model()

ExperimentQuerySet = Union[QuerySet, List[Experiment]]
ScoreSetQuerySet = Union[QuerySet, List[ScoreSet]]


def search_view(request):
    if request.is_ajax():
        try:
            data = process_search_request(request)
            data["draw"] = int(request.POST.get("draw"))
            data["error"] = None
            return JsonResponse(data=data, status=200)
        except Exception as error:
            return JsonResponse(data={"message": str(error)}, status=500)
    return render(request, "search/search.html")


def process_search_request(request) -> Dict:
    basic_form, adv_form = format_datatables_search(request)

    user = request.user
    # Don't use distinct query yet because django cannot combine unique
    # queries with non-unique queries during the filtering stage.
    experiments = filter_visible(
        Experiment.objects.all(), user=user, distinct=False
    )
    scoresets = filter_visible(
        ScoreSet.objects.all(), user=user, distinct=False
    )
    total_count = scoresets.distinct().count()

    # Filter based on advanced search first because it's quicker and
    # will reduce the number of items we need to full text search on next
    if adv_form and adv_form.is_valid():
        data = adv_form.format_data_for_filter()
        experiment_filter = ExperimentFilter(
            data=data, request=request, queryset=experiments
        )
        scoreset_filter = ScoreSetFilter(
            data=data, request=request, queryset=scoresets
        )
        experiments = experiment_filter.qs
        scoresets = scoreset_filter.qs

    # Further filter results if the search box is used using full-text search
    if basic_form and basic_form.is_valid():
        data = basic_form.format_data_for_filter()
        experiment_filter = ExperimentFilter(
            data=data, request=request, queryset=experiments
        )
        scoreset_filter = ScoreSetFilter(
            data=data, request=request, queryset=scoresets
        )
        experiments = experiment_filter.qs_or
        scoresets = scoreset_filter.qs_or

    try:
        per_page = int(request.POST.get("length"))
    except (ValueError, TypeError):
        per_page = 10

    try:
        # Convert to 1-based to get record number so correct page can
        # be computed.
        start = int(request.POST.get("start")) + 1
        page_num = math.ceil(start / per_page)
    except (ValueError, TypeError):
        page_num = 1

    # Build the search pane options from results found from search pane
    # query parameters only
    all_scoresets = combine_scoresets(experiments, scoresets, user)
    datatables_data = {
        "searchPanes": format_search_panes_options(
            scoresets=all_scoresets,
            user=user,
        )
    }

    datatables_data.update(
        format_datatables_response(
            scoresets=all_scoresets,
            user=user,
            order_by=request.POST.get("order[0][column]"),
            order_dir=request.POST.get("order[0][dir]"),
            page_num=page_num,
            per_page=per_page,
            total_count=total_count,
        )
    )
    return datatables_data


def combine_scoresets(
    experiments: ExperimentQuerySet, scoresets: ScoreSetQuerySet, user: User
) -> ScoreSetQuerySet:
    for experiment in filter_visible(experiments, user=user, distinct=True):
        scoresets |= experiment.children

    scoresets = scoresets.filter(
        pk__in=set(i.get_current_version(user).pk for i in scoresets)
    )
    return filter_visible(scoresets, user=user, distinct=True)


def format_datatables_search(request) -> Tuple[Form, Optional[Form]]:
    adv_form = None
    basic_form = None

    data = {}
    targets = [
        target
        for key, target in request.POST.items()
        if "searchPanes[target]" in key
    ]
    target_types = [
        target_type
        for key, target_type in request.POST.items()
        if "searchPanes[type]" in key
    ]

    organisms = [
        organism.replace("<i>", "").replace("</i>", "")
        for key, organism in request.POST.items()
        if "searchPanes[organism]" in key
    ]

    if targets:
        data["target"] = ",".join(targets)
    if target_types:
        data["target_type"] = ",".join(target_types)
    if organisms:
        data["organism"] = ",".join(organisms)

    if data:
        adv_form = forms.AdvancedSearchForm(data=data)

    basic_search = request.POST.get("search[value]")
    if basic_search:
        basic_form = forms.BasicSearchForm(data={"search": basic_search})

    return basic_form, adv_form


def format_datatables_response(
    scoresets: ScoreSetQuerySet,
    user: User,
    order_by: str = "0",
    order_dir: str = "asc",
    per_page: int = 10,
    page_num: int = 1,
    total_count: Optional[int] = None,
) -> Dict:
    # Apply ordering using data-tables POST parameters
    scoresets = order_scoresets(
        scoresets=scoresets, column=order_by, direction=order_dir
    ).distinct()

    paginator = Paginator(object_list=scoresets, per_page=per_page)
    if page_num > paginator.num_pages:
        page_num = paginator.num_pages
    page: Page = paginator.page(page_num)
    print(page.object_list.count())

    # JSON record data for data-tables
    data = []
    seen = set()
    for scoreset in page.object_list:
        scoreset = scoreset.get_current_version(user=user)

        # Older scoresets returned from search might map to same current
        # version.
        if scoreset.urn in seen:
            continue
        else:
            seen.add(scoreset.urn)

        names, types, orgs = display_targets(scoreset, user, all_fields=True)
        data.append(
            {
                "urn": scoreset.urn,
                "urn_display": format_urn_name_for_user(scoreset, user),
                "description": scoreset.short_description,
                "target": names,
                "type": types,
                "organism": orgs,
                "parent_urn": scoreset.parent.urn,
                "parent_urn_display": format_urn_name_for_user(
                    scoreset.parent, user
                ),
                "parent_description": scoreset.parent.short_description,
            }
        )

    return {
        "recordsFiltered": scoresets.count(),
        "recordsTotal": total_count,
        "data": data,
    }


def order_scoresets(
    scoresets: ScoreSetQuerySet, column: str, direction: str
) -> ScoreSetQuerySet:
    if column == "0":
        field = "urn"
    elif column == "1":
        field = "short_description"
    elif column == "2":
        field = "target__name"
    elif column == "3":
        field = "target__category"
    elif column == "4":
        field = "target__reference_maps__genome__organism_name"
    else:
        raise ValueError(f"Unknown data-tables column index '{column}'")

    if direction == "desc":
        field = "-" + field

    return scoresets.all().order_by(field)


def format_search_panes_options(
    scoresets: ScoreSetQuerySet, user: User
) -> Dict:
    options_targets = []
    options_target_types = []
    options_target_orgs = []

    for scoreset in scoresets:
        name, t_type, org = display_targets(scoreset, user, all_fields=True)
        options_targets.append(name)
        options_target_types.append(t_type)
        options_target_orgs.append(org)

    return {
        "options": {
            "target": [
                {"label": k, "value": k, "count": count, "total": count}
                for k, count in Counter(options_targets).items()
            ],
            "type": [
                {"label": k, "value": k, "count": count, "total": count}
                for k, count in Counter(options_target_types).items()
            ],
            "organism": [
                {"label": k, "value": k, "count": count, "total": count}
                for k, count in Counter(options_target_orgs).items()
            ],
        }
    }
