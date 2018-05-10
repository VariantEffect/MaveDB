"""
Add any functions here which you would like for use in templates.
"""
from main.models import SiteInformation

def baseurl(request):
    """
    Return a BASE_URL template context for the current request.
    """
    if request.is_secure():
        scheme = 'https://'
    else:
        scheme = 'http://'

    return {
        'BASE_URL': scheme + request.get_host(),
    }


def site_information(request):
    """Adds the SiteInformation singleton to all requests."""
    return {'site_information': SiteInformation.get_instance()}