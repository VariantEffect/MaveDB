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
    experiments = Experiment.objects.all()[0: 1000]
    
    if request.method == "POST":
        form = AdvancedSearchForm(request.POST)
        scoring_methods = [x.strip() for x in form.data['scoring_methods'].split(",")]
        experiments = Experiment.objects.filter(scoring_method__in=scoring_methods)
        
    return render(
        request=request,
        template_name='main/search.html',
        context={
            'experiments': experiments,
            'basic_search_form': basic_search_form,
            'advanced_search_form': advanced_search_form
        }
    )
