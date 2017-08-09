from django.shortcuts import render, redirect
from django.http import StreamingHttpResponse

from .models import News, SiteInformation


def home_view(request):
    news_items = News.recent_news()
    return render(request, 'main/home.html', {
        "news_items": news_items,
        "site_information": SiteInformation.get_instance()
    })


def download_view(request):
    return render(request, 'main/download.html', {})


def upload_view(request):
    form = CreateExperimentForm()
    return render(request, 'main/upload.html', {"form": form})


def login_view(request):
    return render(request, 'main/login.html', {})


def register_view(request):
    return render(request, 'main/register.html', {})


def usage_guide_view(request):
    return render(request, 'main/usage_guide.html', {
        "site_information": SiteInformation.get_instance()
    })


def documentation_view(request):
    return render(request, 'main/documentation.html', {
        "site_information": SiteInformation.get_instance()
    })


def help_contact_view(request):
    return render(request, 'main/help_contact.html', {})


def terms_privacy_view(request):
    return render(request, 'main/terms_privacy.html', {
        "site_information": SiteInformation.get_instance()
    })
