import csv

from rest_framework import viewsets
from rest_framework.response import Response

from django.contrib.auth import get_user_model
from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import cache_page

from accounts.filters import UserFilter

from dataset import models, filters, constants
from dataset.serializers import (
    UserSerializer,
    ExperimentSetSerializer,
    ExperimentSerializer,
    ScoreSetSerializer,
)

from accounts.permissions import PermissionTypes

User = get_user_model()
ScoreSet = models.scoreset.ScoreSet


# ViewSet CBVs for list/detail views
# --------------------------------------------------------------------------- #
class ListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Base API viewset. Must also inherit a subclass of
    :class:`DatasetModelFilterMixin`.
    """
    filter_class = None
    queryset = None

    def list(self, request, *args, **kwargs):
        filter_ = self.filter_class(
            data=request.GET, queryset=self.queryset, request=request)
        serializer = self.serializer_class(filter_.qs, many=True)
        return Response(serializer.data)


class ExperimentSetViewset(ListViewSet):
    serializer_class = ExperimentSetSerializer
    filter_class = filters.ExperimentSetFilterModel
    queryset = models.experimentset.ExperimentSet.objects.filter(private=False)
    lookup_field = 'urn'


class ExperimentViewset(ListViewSet):
    serializer_class = ExperimentSerializer
    filter_class = filters.ExperimentFilter
    queryset = models.experiment.Experiment.objects.filter(private=False)
    lookup_field = 'urn'


class ScoreSetViewset(ListViewSet):
    serializer_class = ScoreSetSerializer
    filter_class = filters.ScoreSetFilter
    queryset = models.scoreset.ScoreSet.objects.filter(private=False)
    lookup_field = 'urn'


class UserViewset(ListViewSet):
    queryset = User.objects.exclude(username='AnonymousUser')
    serializer_class = UserSerializer
    filter_class = UserFilter
    lookup_field = 'username'


# File download FBVs
# --------------------------------------------------------------------------- #
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
