import csv

from rest_framework.viewsets import ReadOnlyModelViewSet

from django.contrib.auth import get_user_model
from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import cache_page

from accounts.mixins import UserFilterMixin

from dataset.models.experimentset import ExperimentSet
from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet
import dataset.constants as constants
from dataset.serializers import (
    UserSerializer,
    ExperimentSetSerializer,
    ExperimentSerializer,
    ScoreSetSerializer,
)

from dataset.mixins import (
    ExperimentSetFilterMixin,
    ExperimentFilterMixin,
    ScoreSetFilterMixin,
)

from accounts.permissions import PermissionTypes

User = get_user_model()


class DatasetModelViewSet(ReadOnlyModelViewSet):
    """
    Base API viewset. Must also inherit a subclass of
    :class:`DatasetModelFilterMixin`.
    """

    def get_queryset(self, exclude_private=True):
        queryset = super().get_queryset()
        query_dict = dict()

        if 'search' in self.request.query_params.keys():
            join_func = self.or_join_qs
            query_dict['search'] = self.request.query_params.getlist(
                'search', [])
        else:
            join_func = self.and_join_qs
            for field in self.search_field_to_function():
                if field in self.request.query_params:
                    query_dict[field] = self.request.\
                        query_params.getlist(field, [])

        if query_dict:
            q = self.search_all(query_dict, join_func)
            queryset = queryset.filter(q).distinct()

        return queryset.exclude(private=exclude_private)


class ExperimentSetViewset(DatasetModelViewSet, ExperimentSetFilterMixin):
    queryset = ExperimentSet.objects.filter(private=False)
    serializer_class = ExperimentSetSerializer
    lookup_field = 'urn'


class ExperimentViewset(DatasetModelViewSet, ExperimentFilterMixin):
    queryset = Experiment.objects.filter(private=False)
    serializer_class = ExperimentSerializer
    lookup_field = 'urn'


class ScoreSetViewset(DatasetModelViewSet, ScoreSetFilterMixin):
    queryset = ScoreSet.objects.filter(private=False)
    serializer_class = ScoreSetSerializer
    lookup_field = 'urn'


class UserViewset(ReadOnlyModelViewSet, UserFilterMixin):
    queryset = User.objects.exclude(username='AnonymousUser')
    serializer_class = UserSerializer
    lookup_field = 'username'

    def get_queryset(self):
        queryset = super().get_queryset()
        query_dict = dict()

        if 'search' in self.request.query_params.keys():
            join_func = self.or_join_qs
            query_dict['search'] = self.request.query_params.getlist(
                'search', [])
        else:
            join_func = self.and_join_qs
            for field in self.search_field_to_function():
                if field in self.request.query_params:
                    query_dict[field] = self.request. \
                        query_params.getlist(field, [])

        if query_dict:
            q = self.search_all(query_dict, join_func)
            queryset = queryset.filter(q).distinct()

        return queryset


def _format_csv_rows(variants, columns, variant_column):
    rows = []
    for variant in variants:
        data = []
        for column_key in columns:
            if column_key == constants.hgvs_column:
                data.append('{}'.format(variant.hgvs))
            else:
                data.append(str(variant.data[variant_column][column_key]))
        rows.append(data)
    return rows


def validate_request(urn, user):
    if not ScoreSet.objects.filter(urn=urn).count():
        response = JsonResponse({'detail': '{} does not exist.'.format(urn)})
        response.status_code = 404
        return response
    scoreset = ScoreSet.objects.get(urn=urn)
    has_permission = user.has_perm(PermissionTypes.CAN_VIEW, scoreset)
    if scoreset.private and not has_permission:
        response = JsonResponse({'detail': '{} is private.'.format(urn)})
        response.status_code = 404
        return response
    return scoreset


@cache_page(60 * 1440) # 24 hour cache
def scoreset_score_data(request, urn):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = \
        'attachment; filename="{}_scores.csv"'.format(urn)
    
    scoreset_or_response = validate_request(urn, request.user)
    if not isinstance(scoreset_or_response, ScoreSet):
        return scoreset_or_response

    scoreset = scoreset_or_response
    variants = scoreset.children.order_by("urn")
    columns = scoreset.score_columns
    variant_column = constants.variant_score_data
    if not variants or len(columns) <= 1:  # HGVS is present by default
        return response
    
    writer = csv.writer(response)
    writer.writerow(columns)
    rows = _format_csv_rows(variants, columns, variant_column)
    for row in rows:
        writer.writerow(row)
    return response


@cache_page(60 * 1440) # 24 hour cache
def scoreset_count_data(request, urn):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = \
        'attachment; filename="{}_counts.csv"'.format(urn)

    scoreset_or_response = validate_request(urn, request.user)
    if not isinstance(scoreset_or_response, ScoreSet):
        return scoreset_or_response
    
    scoreset = scoreset_or_response
    variants = scoreset.children.order_by("urn")
    columns = scoreset.count_columns
    variant_column = constants.variant_count_data
    if not variants or len(columns) <= 1:  # HGVS is present by default
        return response
    
    writer = csv.writer(response)
    writer.writerow(columns)
    rows = _format_csv_rows(variants, columns, variant_column)
    for row in rows:
        writer.writerow(row)
    return response


@cache_page(60 * 1440) # 24 hour cache
def scoreset_metadata(request, urn):
    scoreset_or_response = validate_request(urn, request.user)
    if not isinstance(scoreset_or_response, ScoreSet):
        return scoreset_or_response
    scoreset = scoreset_or_response
    return JsonResponse(scoreset.extra_metadata)
