"""
Add any functions here which you would like for use in templates.
"""
from core.utilities import base_url


def baseurl(request=None):
    """
    Return a base_url template context for the current request.
    """
    return {"base_url": base_url(request)}


def site_information(request):
    """Adds the SiteInformation singleton to all requests."""
    from .models import SiteInformation

    return {"site_information": SiteInformation.get_instance()}
