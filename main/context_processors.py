"""
Add any functions here which you would like for use in templates.
"""
from django.conf import settings


def baseurl(request):
    """
    Return a base_url template context for the current request.
    """
    if request is None:
        scheme = 'http://'
    else:
        if request.is_secure():
            scheme = 'https://'
        else:
            scheme = 'http://'
    return {'base_url': scheme + settings.HOST_NAME}


def site_information(request):
    """Adds the SiteInformation singleton to all requests."""
    from .models import SiteInformation
    return {'site_information': SiteInformation.get_instance()}
