import csv

from django.core.exceptions import ImproperlyConfigured

from django_filters import filters


class MultiCharFilter(filters.CharFilter):
    sep = None

    def filter(self, qs, value):
        if not self.sep:
            raise ImproperlyConfigured(
                "MultiCharFilter is abstract and cannot be instantiated."
            )
        if value:
            value = list(csv.reader([value], delimiter=self.sep))[0]
        if not isinstance(value, list):
            value = [value]
        result = qs.none()
        for v in value:
            result |= super().filter(qs, v)
        return result


class CSVCharFilter(MultiCharFilter):
    sep = ","
