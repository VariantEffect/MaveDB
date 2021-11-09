from django.utils.deprecation import MiddlewareMixin

# This version supports Django 1.


class CorsMiddleware(MiddlewareMixin):
    """CORS middleware

    Methods
    -------
    process_response(request, response)
      Add a CORS header to the HTTP response.
    """

    def process_response(self, request, response):
        """Add a CORS Access-Control-Allow-Origin=* header to the response.

        This allows API responses to be consumed by browser-based clients.

        Parameters
        ----------
        request : HttpRequest
          The current HTTP request
        response : HttpResponse
          The HTTP response to which a CORS header should be added

        Returns
        -------
        The HTTP response
        """
        response["Access-Control-Allow-Origin"] = "*"
        return response


# For later versions of Django:
# def cors_middleware(get_response):
#   # One-time configuration and initialization.
#
#   def middleware(request):
#     # Code to be executed for each request before
#     # the view (and later middleware) are called.
#     response = get_response(request)
#     response["Access-Control-Allow-Origin"] = "*"
#     return response
#
#   return middleware
