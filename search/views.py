from django.shortcuts import render
from django.contrib.auth import get_user_model

from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet
from dataset.filters import ScoreSetFilter, ExperimentFilter

from . import forms

User = get_user_model()

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

    instances = list(scoresets.distinct()) + list(experiments.distinct())
    context = {
        "b_search_form": b_search_form,
        "adv_search_form": adv_search_form,
        "instances": instances,
    }
    return render(request, "search/search.html", context)
