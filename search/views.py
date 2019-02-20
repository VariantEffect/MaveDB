import json

from django.shortcuts import render
from django.contrib.auth import get_user_model

from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet
from dataset.templatetags.dataset_tags import \
    format_urn_name_for_user, display_targets, filter_visible
from dataset.filters import ScoreSetFilter, ExperimentFilter

from . import forms


User = get_user_model()


def group_children(parents, children, user):
    grouped = {p: set() for p in parents}
    for child in children:
        if not child.get_current_version(user).private:
            child = child.get_current_version()
        elif child.get_current_version().private \
            and user in child.get_current_version(user).contributors():
            child = child.get_current_version(user)
        
        if child.parent in grouped:
            grouped[child.parent].add(child)
        else:
            grouped[child.parent] = {child}
    grouped = {
        p: list(sorted(v, key=lambda i: i.urn)) for (p, v) in grouped.items()
    }
    return grouped


def to_json(groups, user):
    data = []
    for parent, children in groups.items():
        child_data = []
        for child in children:
            contributors = []
            for c in child.contributors():
                contributors.append(
                    "<span>{}{}</span><br>".format(
                        c.profile.get_display_name_hyperlink(),
                        '<i class="external-link-small '
                        'fas fa-external-link-alt"></i>'
                    ))
            child_data.append({
                "urn": '<a href="{}">{}</a>'.format(
                    child.get_url(),
                    format_urn_name_for_user(child, user)
                ),
                "description": child.short_description,
                "target": display_targets(child, user),
                "type": display_targets(child, user, categories=True),
                "organism": display_targets(child, user, organisms=True),
                "contributors": ''.join(contributors),
            })

        contributors = []
        for c in parent.contributors():
            contributors.append(
                "<span>{}{}</span><br>".format(
                    c.profile.get_display_name_hyperlink(),
                    '<i class="external-link-small '
                    'fas fa-external-link-alt"></i>'
                ))
        data.append({
            "urn": '<a href="{}">{}</a>'.format(
                parent.get_url(),
                format_urn_name_for_user(parent, user)
            ),
            "description": parent.short_description,
            "target": display_targets(parent, user),
            "type": display_targets(parent, user, categories=True),
            "organism": display_targets(parent, user, organisms=True),
            "contributors": ''.join(contributors),
            "children": child_data,
        })
    return data


def search_view(request):
    b_search_form = forms.BasicSearchForm()
    adv_search_form = forms.AdvancedSearchForm()
    experiments = Experiment.objects.all()
    scoresets = ScoreSet.objects.all()
    
    if request.method == 'GET':
        if 'search' in request.GET:
            form = forms.BasicSearchForm(data=request.GET)
        else:
            form = forms.AdvancedSearchForm(data=request.GET)

        if form.is_valid():
            data = form.format_data_for_filter()
            experiment_filter = ExperimentFilter(
                data=data, request=request, queryset=experiments
            )
            scoreset_filter = ScoreSetFilter(
                data=data, request=request, queryset=scoresets
            )
            if isinstance(form, forms.BasicSearchForm):
                experiments = experiment_filter.qs_or
                scoresets = scoreset_filter.qs_or
            else:
                experiments = experiment_filter.qs
                scoresets = scoreset_filter.qs


    instances = group_children(
        parents=filter_visible(experiments.distinct(), request.user),
        children=filter_visible(scoresets.distinct(), request.user),
        user=request.user,
    )
    context = {
        "b_search_form": b_search_form,
        "adv_search_form": adv_search_form,
        "instances": json.dumps(to_json(instances, user=request.user)),
    }
    return render(request, "search/search.html", context)
