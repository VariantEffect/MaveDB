from django_filters import filters, FilterSet

from django.contrib.auth import get_user_model

from accounts.mixins import filter_anon

from core.filters import CSVCharFilter

User = get_user_model()


class UserFilter(FilterSet):
    """
    Filter for the model `User` on fields:
        - username
        - first_name
        - last_name
        - display_name
    """
    FIRST_NAME = 'first_name'
    LAST_NAME = 'last_name'
    USERNAME = 'username'
    DISPLAY_NAME = 'display_name'

    class Meta:
        queryset = User.objects.filter(is_superuser=False)
        model = User
        fields = (
            'first_name', 'last_name', 'username', 'display_name',
        )

    first_name = CSVCharFilter(
        field_name='first_name', lookup_expr='iexact')
    last_name = CSVCharFilter(
        field_name='last_name', lookup_expr='iexact')
    username = CSVCharFilter(
        field_name='username', lookup_expr='iexact')
    display_name = CSVCharFilter(method='filter_by_display_name')

    @property
    def qs(self):
        qs = super().qs
        return filter_anon(qs.filter(is_superuser=False))

    def filter_by_display_name(self, queryset, name, value):
        queryset = filter_anon(queryset.filter(is_superuser=False))
        instances_pks = []
        if not queryset.count():
            return queryset
        model = queryset.first().__class__
        for instance in queryset.all():
            if value.lower() in instance.profile.get_display_name().lower():
                instances_pks.append(instance.pk)
        return model.objects.filter(pk__in=set(instances_pks))
