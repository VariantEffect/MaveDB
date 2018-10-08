from django.shortcuts import render
from django.contrib.auth import get_user_model

from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet
from dataset.filters import ScoreSetFilter, ExperimentFilter

from . import forms

User = get_user_model()


def group_children(parents, children):
    grouped = {p: set() for p in parents}
    for child in children:
        if child.parent in grouped:
            grouped[child.parent].add(child)
        else:
            grouped[child.parent] = {child}
    grouped = {p: list(reversed(sorted(v, key=lambda i: i.urn)))
               for (p, v) in grouped.items()}
    return grouped


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
                data=data, request=request, queryset=experiments)
            scoreset_filter = ScoreSetFilter(
                data=data, request=request, queryset=scoresets)

            if isinstance(form, forms.BasicSearchForm):
                experiments = experiment_filter.qs_or
                scoresets = scoreset_filter.qs_or
            else:
                experiments = experiment_filter.qs
                scoresets = scoreset_filter.qs

    instances = group_children(
        list(experiments.distinct().order_by('urn')),
        list(scoresets.distinct().order_by('urn'))
    )
    context = {
        "b_search_form": b_search_form,
        "adv_search_form": adv_search_form,
        "instances": instances,
    }
    return render(request, "search/search.html", context)
