import csv

from rest_framework import viewsets, exceptions
from rest_framework.response import Response

from django.contrib.auth import get_user_model
from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import cache_page

from accounts.models import AUTH_TOKEN_RE, Profile
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
class DatasetListViewSet(viewsets.ReadOnlyModelViewSet):
    filter_class = None

    @staticmethod
    def _authenticate(token):
        if not token:
            return None
        profiles = Profile.objects.filter(auth_token=token)
        if profiles.count():
            profile = profiles.first()
            if profile.auth_token_is_valid(token):
                return profile.user
        return None

    def dispatch(self, request, *args, **kwargs):
        token = request.META.get('HTTP_AUTHORIZATION', None)
        self.auth_token = None
        if token is not None:
            if not AUTH_TOKEN_RE.fullmatch(token):
                self.auth_token = None
            else:
                self.auth_token = token
        self.user = self._authenticate(self.auth_token)
        return super().dispatch(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        filter_ = self.filter_class(
            data=request.GET, queryset=self.queryset, request=request)
        queryset = filter_.qs
        if self.user is None and self.auth_token:
            raise exceptions.PermissionDenied(
                detail='Invalid authentication token.'
            )
        elif self.user is not None:
            queryset = filter_.filter_for_user(user=self.user, qs=queryset)
        else:
            queryset = queryset.filter(private=False)
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.private and self.auth_token is None:
            raise exceptions.PermissionDenied(
                detail='Authentication token missing.')
        elif instance.private and self.auth_token is not None:
            valid_token = any([
                user.profile.auth_token_is_valid(self.auth_token)
                for user in instance.contributors()
            ])
            if not valid_token:
                raise exceptions.PermissionDenied(
                    detail='Invalid authentication token.'
                )
            return super().retrieve(request, *args, **kwargs)
        else:
            return super().retrieve(request, *args, **kwargs)


class ExperimentSetViewset(DatasetListViewSet):
    serializer_class = ExperimentSetSerializer
    filter_class = filters.ExperimentSetFilterModel
    queryset = models.experimentset.ExperimentSet.objects.filter()
    lookup_field = 'urn'


class ExperimentViewset(DatasetListViewSet):
    serializer_class = ExperimentSerializer
    filter_class = filters.ExperimentFilter
    queryset = models.experiment.Experiment.objects.filter()
    lookup_field = 'urn'


class ScoreSetViewset(DatasetListViewSet):
    serializer_class = ScoreSetSerializer
    filter_class = filters.ScoreSetFilter
    queryset = models.scoreset.ScoreSet.objects.filter()
    lookup_field = 'urn'


class UserViewset(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.exclude(username='AnonymousUser')
    serializer_class = UserSerializer
    filter_class = UserFilter
    lookup_field = 'username'

    def list(self, request, *args, **kwargs):
        filter_ = self.filter_class(
            data=request.GET, queryset=self.queryset, request=request)
        serializer = self.serializer_class(filter_.qs, many=True)
        return Response(serializer.data)


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
