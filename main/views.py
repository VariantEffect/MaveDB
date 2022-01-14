from collections import Counter

from django.shortcuts import render, redirect
from django.contrib import messages

from dataset.models.scoreset import ScoreSet
from dataset.models.experiment import Experiment

from .models import News, SiteInformation


def get_top_n(n, ls):
    counter = list(Counter(ls).items())
    return [i for i, count in sorted(counter, key=lambda x: x[1])[-n:]]


def home_view(request):
    # Tuples are required to allow search GET requests to be contructed from the
    # organism raw text instead of the formatted text. The other fields are
    # tuple-ized for template compatibility.
    news_items = News.recent_news()
    organism = [
        (g.get_organism_name(), g.format_organism_name_html())
        for s in ScoreSet.objects.exclude(private=True)
        for g in s.get_target().get_reference_genomes()
    ]
    targets = [
        (s.get_target().get_name(), s.get_target().get_name())
        for s in ScoreSet.objects.exclude(private=True)
    ]
    keywords = [
        (k.text, k.text)
        for s in Experiment.objects.exclude(private=True)
        for k in s.keywords.all()
    ]
    keywords += [
        (k.text, k.text)
        for s in ScoreSet.objects.exclude(private=True)
        for k in s.keywords.all()
    ]

    return render(
        request,
        "main/home.html",
        {
            "news_items": news_items,
            "site_information": SiteInformation.get_instance(),
            "top_organisms": sorted(get_top_n(3, organism)),
            "top_targets": sorted(get_top_n(3, targets)),
            "top_keywords": sorted(get_top_n(3, keywords)),
            "all_organisms": sorted(set([i[0] for i in organism])),
            "all_targets": sorted(set([i[0] for i in targets])),
        },
    )


def documentation_view(request):
    return render(
        request,
        # "main/documentation.html",
        "main/new_documentation.html",
        {"site_information": SiteInformation.get_instance()},
    )


def help_contact_view(request):
    return render(
        request,
        "main/help_contact.html",
        {
            "site_information": SiteInformation.get_instance(),
        },
    )


def terms_privacy_view(request):
    return render(
        request,
        "main/terms_privacy.html",
        {"site_information": SiteInformation.get_instance()},
    )


def handler403(request, exception=None, template_name="main/403.html"):
    response = render(request, template_name, context={})
    response.status_code = 403
    return response


def handler404(request, exception=None, template_name="main/404.html"):
    response = render(request, template_name, context={})
    response.status_code = 404
    return response


def handler500(request, exception=None, template_name="main/500.html"):
    response = render(request, template_name, context={})
    response.status_code = 500
    return response


def robots(request):
    return render(request, "main/robots.txt", content_type="text/plain")
