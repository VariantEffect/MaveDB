from collections import Counter

from django.shortcuts import render, redirect
from django.contrib import messages

from dataset.models.scoreset import ScoreSet
from dataset.models.experiment import Experiment

from .models import News, SiteInformation
from .forms import ContactForm


def get_top_n(n, ls):
    counter = list(Counter(ls).items())
    top_n = [i for i, _ in sorted(counter, key=lambda x: x[1])[0:n]]
    return top_n


def home_view(request):
    news_items = News.recent_news()
    species = [
        (g.get_species_name(), g.format_species_name_html())
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

    return render(request, 'main/home.html', {
        "news_items": news_items,
        "site_information": SiteInformation.get_instance(),
        "top_species": sorted(get_top_n(3, species)),
        "top_targets": sorted(get_top_n(3, targets)),
        "top_keywords": sorted(get_top_n(3, keywords)),
        "all_species": sorted(set([i[0] for i in species])),
        "all_targets": sorted(set([i[0] for i in targets]))
    })


def documentation_view(request):
    return render(request, 'main/documentation.html', {
        "site_information": SiteInformation.get_instance()
    })


def help_contact_view(request):
    contact_form = ContactForm()
    if request.method == 'POST':
        contact_form = ContactForm(data=request.POST)
        if contact_form.is_valid():
            contact_form.send_mail()
            messages.success(
                request,
                "Thank you for contacting us. We've sent a confirmation email "
                "to your nominated contact address."
            )
            return redirect('main:contact')

    return render(request, 'main/help_contact.html', {
        "site_information": SiteInformation.get_instance(),
        'contact_form': contact_form
    })


def terms_privacy_view(request):
    return render(request, 'main/terms_privacy.html', {
        "site_information": SiteInformation.get_instance()
    })


def handler403(request, exception=None, template_name='main/403.html'):
    response = render(
        request, template_name, context={})
    response.status_code = 403
    return response


def handler404(request, exception=None, template_name='main/404.html'):
    response = render(
        request, template_name, context={})
    response.status_code = 404
    return response


def handler500(request, exception=None, template_name='main/500.html'):
    response = render(
        request, template_name, context={})
    response.status_code = 500
    return response


def robots(request):
    return render(request, 'main/robots.txt', content_type='text/plain')
