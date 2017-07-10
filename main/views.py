from django.shortcuts import render
from django.http import HttpResponse

from .models import News, SiteInformation


def home_view(request):
    news_items = News.recent_news()
    if SiteInformation.objects.count() == 1:
        site_information = SiteInformation.objects.all()[0]
        return render(request, 'main/home.html', {
            "news_items": news_items, "site_information": site_information})
    else:
        return render(request, 'main/home.html', {"news_items": news_items})


def search_view(request):
    return render(request, 'main/search.html')
