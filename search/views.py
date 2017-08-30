from django.shortcuts import render

from experiment.models import Experiment
from .forms import SearchForm


def search_view(request):
    form = SearchForm()
    context = {"form": form}
    return render(request, "search/search.html", context)
