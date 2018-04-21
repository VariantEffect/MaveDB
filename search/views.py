from django.shortcuts import render

from dataset.models.experiment import Experiment
from accounts.permissions import user_is_anonymous

from .forms import SearchForm


def search_view(request):
    form = SearchForm()
    experiments = Experiment.objects.all()

    if request.method == "GET":
        form = SearchForm(request.GET)
        if form.is_valid():
            experiments = form.query_experiments()

    context = {
        "form": form,
        "experiments": experiments,
    }

    return render(request, "search/search.html", context)
