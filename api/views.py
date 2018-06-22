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


@cache_page(60 * 15) # 15 minute cache
def scoreset_score_data(request, urn):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = \
        'attachment; filename="{}_scores.csv"'.format(urn)
    
    scoreset_or_response = validate_request(urn, request.user)
    if not isinstance(scoreset_or_response, ScoreSet):
        return scoreset_or_response

    scoreset = scoreset_or_response
    variants = scoreset.children.order_by('{}'.format(
        scoreset.primary_hgvs_column))
    columns = scoreset.score_columns
    type_column = constants.variant_score_data
    # hgvs_nt and hgvs_pro present by default, hence <= 2
    if not variants or len(columns) <= 2:
        return response
    
    writer = csv.DictWriter(
        response, fieldnames=columns, quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    writer.writerows(_format_csv_rows(variants, columns, type_column))
    return response


@cache_page(60 * 15) # 15 minute cache
def scoreset_count_data(request, urn):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = \
        'attachment; filename="{}_counts.csv"'.format(urn)

    scoreset_or_response = validate_request(urn, request.user)
    if not isinstance(scoreset_or_response, ScoreSet):
        return scoreset_or_response
    
    scoreset = scoreset_or_response
    variants = scoreset.children.order_by('{}'.format(
        scoreset.primary_hgvs_column))
    columns = scoreset.count_columns
    type_column = constants.variant_count_data
    # hgvs_nt and hgvs_pro present by default, hence <= 2
    if not variants or len(columns) <= 2:
        return response
    
    writer = csv.DictWriter(
        response, fieldnames=columns, quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    writer.writerows(_format_csv_rows(variants, columns, type_column))
    return response


def _format_csv_rows(variants, columns, type_column):
    rowdicts = []
    for variant in variants:
        data = {}
        for column_key in columns:
            if column_key == constants.hgvs_nt_column:
                data[column_key] = variant.hgvs_nt
            elif column_key == constants.hgvs_pro_column:
                data[column_key] = variant.hgvs_pro
            else:
                data[column_key] = str(variant.data[type_column][column_key])
        rowdicts.append(data)
    return rowdicts


@cache_page(60 * 15) # 24 hour cache
def scoreset_metadata(request, urn):
    scoreset_or_response = validate_request(urn, request.user)
    if not isinstance(scoreset_or_response, ScoreSet):
        return scoreset_or_response
    scoreset = scoreset_or_response
    return JsonResponse(scoreset.extra_metadata)
