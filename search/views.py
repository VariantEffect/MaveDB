from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

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

    if user_is_anonymous(request.user):
        experiments = [e for e in experiments if not e.private]
        has_data = len(experiments) > 0
    else:
        users_experiments = request.user.profile.contributor_experiments()
        private_experiments = [
            e for e in experiments if e.private and e in users_experiments
        ]
        public_experiments = [e for e in experiments if not e.private]
        has_data = len(private_experiments) > 0 or len(public_experiments) > 0

    # Handle the pagination request options
    try:
        per_page = request.GET.get('per-page', 25)
        per_page = int(per_page)
    except:
        per_page = 25

    paginator = Paginator(experiments, per_page=per_page)
    try:
        page_num = request.GET.get('page', 1)
    except PageNotAnInteger:
        page_num = 1
    except EmptyPage:
        page_num = paginator.num_pages

    experiments = paginator.page(page_num)
    context = {
        "form": form,
        "contributor_experiments": experiments,
        "has_data": has_data,
        "per_page": per_page,
        "page_num": page_num,
        "per_page_selections": [25, 50, 100]
    }

    return render(request, "search/search.html", context)
