from django.shortcuts import render
from django.http import HttpResponse

from .models import News, SiteInformation, Experiment
from .forms import BasicSearchForm, AdvancedSearchForm


def home_view(request):
    news_items = News.recent_news()
    if SiteInformation.objects.count() == 1:
        site_information = SiteInformation.objects.all()[0]
        return render(request, 'main/home.html', {
            "news_items": news_items, "site_information": site_information})
    else:
        return render(request, 'main/home.html', {"news_items": news_items})


def search_view(request):
    basic_search_form = BasicSearchForm()
    advanced_search_form = AdvancedSearchForm()
    experiments = Experiment.objects.all()

    if request.method == "POST":
        advanced_search_form = AdvancedSearchForm(request.POST)
        if advanced_search_form.is_valid():
            experiments = advanced_search_form.query_experiments()

    return render(
        request=request,
        template_name='main/search.html',
        context={
            'experiments': experiments.order_by('?'),
            'basic_search_form': basic_search_form,
            'advanced_search_form': advanced_search_form
        }
    )
