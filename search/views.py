from django.shortcuts import render

# Create your views here.


def search_view(request):
    return render(request, "main/404_not_found.html")
