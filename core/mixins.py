from django.http import JsonResponse


class SingletonMixin:
    """
    A singleton abstract model which allows only once instance(row) to exist.
    Must be the first class inherited to work.
    """

    def save(self, *args, **kwargs):
        self.pk = 1
        super(SingletonMixin, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class NestedEnumMixin:
    """Nested `Enum` of error messages relating to specific fields."""

    def __getattr__(self, item):
        """Allows this `Enum` to be nested by customising attribute lookup."""
        if item != "_value_":
            return getattr(self.value, item).value
        raise AttributeError


class AjaxView:
    """
    Use this mixin in any view which supports an AJAX entry point.
    """

    @staticmethod
    def error(payload, status_code=None):
        response = JsonResponse(data={"error": payload})
        if status_code:
            response.status_code = status_code
        return response

    def get(self, request, *args, **kwargs):
        if request.is_ajax() and hasattr(self, "get_ajax"):
            return self.get_ajax(*args, **kwargs)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.is_ajax() and hasattr(self, "post_ajax"):
            return self.post_ajax(*args, **kwargs)
        return super().post(request, *args, **kwargs)
