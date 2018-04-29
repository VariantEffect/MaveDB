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


def handler404(request, exception=None, template_name='main/404.html'):
    response = render(
        request, template_name, context={})
    response.status_code = 404
    return response


def handler403(request, exception=None, template_name='main/403.html'):
    response = render(
        request, template_name, context={})
    response.status_code = 403
    return response


def handler500(request, exception=None, template_name='main/500.html'):
    response = render(
        request, template_name, context={})
    response.status_code = 500
    return response


