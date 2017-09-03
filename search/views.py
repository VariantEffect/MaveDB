from django.shortcuts import render

from experiment.models import Experiment
from scoreset.models import ScoreSet

from .forms import SearchForm


def search_view(request):
    form = SearchForm()
    experiments = Experiment.objects.all()
    scoresets = ScoreSet.objects.all()
    if request.method == "GET":
        form = SearchForm(request.GET)
        if form.is_valid():
            experiments = form.query_experiments()
            scoresets = form.query_scoresets()
            print(scoresets)

    context = {
        "form": form,
        'experiments': experiments,
        'scoresets': scoresets
    }
    return render(request, "search/search.html", context)
