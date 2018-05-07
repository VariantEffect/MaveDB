"""
Add any functions here which you would like for use in templates.
"""

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