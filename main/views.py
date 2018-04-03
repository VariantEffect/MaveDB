from django.shortcuts import render

from .models import News, SiteInformation


def home_view(request):
    news_items = News.recent_news()
    return render(request, 'main/home.html', {
        "news_items": news_items,
        "site_information": SiteInformation.get_instance()
    })


def documentation_view(request):
    return render(request, 'main/documentation.html', {
        "site_information": SiteInformation.get_instance()
    })


def help_contact_view(request):
    return render(request, 'main/help_contact.html', {
        "site_information": SiteInformation.get_instance()
    })


def terms_privacy_view(request):
    return render(request, 'main/terms_privacy.html', {
        "site_information": SiteInformation.get_instance()
    })
