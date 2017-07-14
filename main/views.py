from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse

from .models import News, SiteInformation, Experiment
from .forms import BasicSearchForm, AdvancedSearchForm


def home_view(request):
    news_items = News.recent_news()
    if SiteInformation.objects.count() == 1:
        site_information = SiteInformation.objects.all()[0]
        return render(request, 'main/home.html', {
            "news_items": news_items,
            "basic_search_form": BasicSearchForm(),
            "site_information": site_information
        })
    else:
        return render(request, 'main/home.html', {
            "news_items": news_items,
            "basic_search_form": BasicSearchForm()
        })


def download_view(request):
    return render(request, 'main/download.html', {})


def upload_view(request):
    return render(request, 'main/upload.html', {})


def login_register_view(request):
    return render(request, 'main/login_register.html', {})


def usage_guide_view(request):
    return render(request, 'main/usage_guide.html', {})


def documentation_view(request):
    return render(request, 'main/documentation.html', {})


def help_contact_view(request):
    return render(request, 'main/help_contact.html', {})


def terms_privacy_view(request):
    return render(request, 'main/terms_privacy.html', {})


def dataset_detail_view(request, accession):
    return render(request, 'main/scoring_method.html', {})


def advanced_search_view(request):
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
            'experiments': experiments,
            'basic_search_form': BasicSearchForm(),
            'advanced_search_form': advanced_search_form
        }
    )


def basic_search_view(request):
    basic_search_form = BasicSearchForm()
    experiments = Experiment.objects.all()

    if request.method == "POST":
        print(request.POST)
        basic_search_form = BasicSearchForm(request.POST)
        if basic_search_form.is_valid():
            experiments = basic_search_form.query_experiments()

    return render(
        request=request,
        template_name='main/search.html',
        context={
            'experiments': experiments,
            'basic_search_form': basic_search_form,
            'advanced_search_form': AdvancedSearchForm()
        }
    )


def search_view(request):
    experiments = Experiment.objects.all()
    return render(
        request=request,
        template_name='main/search.html',
        context={
            'experiments': experiments,
            'basic_search_form': BasicSearchForm(),
            'advanced_search_form': AdvancedSearchForm()
        }
    )


def experiment_detail_view(request, accession):
    experiment = Experiment.objects.all().filter(
        accession__exact=accession.upper())
    try:
        experiment = experiment[0]
    except IndexError:
        experiment = None
    return render(
        request=request,
        template_name='main/experiment.html',
        context={
            'experiment': experiment
        }
    )
