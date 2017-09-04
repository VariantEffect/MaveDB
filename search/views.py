from django.shortcuts import render

from experiment.models import Experiment
from scoreset.models import ScoreSet

from accounts.permissions import user_is_anonymous

from .forms import SearchForm


def search_view(request):
    form = SearchForm()
    experiments = Experiment.objects.all()

    if request.method == "GET":
        form = SearchForm(request.GET)
        if form.is_valid():
            experiments = form.query_experiments()

    if user_is_anonymous(request.user):
        experiments = [e for e in experiments if not e.private]
        has_data = len(experiments) > 0
    else:
        users_experiments = request.user.profile.experiments()
        private_experiments = [
            e for e in experiments if e.private and e in users_experiments
        ]
        public_experiments = [e for e in experiments if not e.private]
        has_data = len(private_experiments) > 0 or len(public_experiments) > 0

    context = {
        "form": form,
        "experiments": experiments,
        "has_data": has_data
    }

    return render(request, "search/search.html", context)
