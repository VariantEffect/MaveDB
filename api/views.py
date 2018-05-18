import csv

from rest_framework.viewsets import ReadOnlyModelViewSet

from django.contrib.auth import get_user_model
from django.http import Http404
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

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


def scoreset_score_data(request, urn):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = \
        'attachment; filename="{}_scores.csv"'.format(urn)
    
    scoreset = get_object_or_404(ScoreSet, urn=urn)
    has_permission = request.user.has_perm(PermissionTypes.CAN_VIEW, scoreset)
    if scoreset.private and not has_permission:
        raise Http404()
    
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


def scoreset_count_data(request, urn):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = \
        'attachment; filename="{}_counts.csv"'.format(urn)
    
    scoreset = get_object_or_404(ScoreSet, urn=urn)
    has_permission = request.user.has_perm(PermissionTypes.CAN_VIEW, scoreset)
    if scoreset.private and not has_permission:
        raise Http404()
    
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


def scoreset_metadata(request, urn):
    scoreset = get_object_or_404(ScoreSet, urn=urn)
    has_permission = request.user.has_perm(PermissionTypes.CAN_VIEW, scoreset)
    if scoreset.private and not has_permission:
        raise Http404()
    return JsonResponse(scoreset.extra_metadata)
