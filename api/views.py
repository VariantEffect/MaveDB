import csv

from rest_framework import viewsets, exceptions

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

User = get_user_model()
ScoreSet = models.scoreset.ScoreSet


def authenticate(request):
    user, token = None, request.META.get('HTTP_AUTHORIZATION', None)
    if not token and request.user and request.user.is_authenticated:
        # As a fallback, check if the current user is authenticated for
        # users using the API via the web interface.
        user, token = request.user, None
    elif token and not AUTH_TOKEN_RE.fullmatch(token):
        # Check the provided token has a valid format.
        raise exceptions.AuthenticationFailed("Invalid token format.")
    elif token and AUTH_TOKEN_RE.fullmatch(token):
        # Otherwise if a valid token has been given, check that it has not
        # expired and that it belongs to one of the site's users.
        profiles = Profile.objects.filter(auth_token=token)
        if profiles.count():
            profile = profiles.first()
            if profile.auth_token_is_valid(token):
                user, token = profile.user, token
            else:
                raise exceptions.AuthenticationFailed("Token has expired.")
        else:
            raise exceptions.AuthenticationFailed("Invalid token.")
    return user, token


def check_permission(instance, user=None):
    if instance.private and user is None:
        raise exceptions.PermissionDenied()
    elif instance.private and user is not None:
        has_perm = user in instance.contributors()
        if not has_perm:
            raise exceptions.PermissionDenied()
    return instance


# ViewSet CBVs for list/detail views
# --------------------------------------------------------------------------- #
class AuthenticatedViewSet(viewsets.ReadOnlyModelViewSet):
    user = None
    auth_token = None
    
    def dispatch(self, request, *args, **kwargs):
        try:
            self.user, self.auth_token = authenticate(request)
            return super().dispatch(request, *args, **kwargs)
        except (exceptions.AuthenticationFailed,
                exceptions.PermissionDenied, exceptions.NotFound) as e:
            return JsonResponse({'detail': e.detail}, status=e.status_code)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['user'] = self.user
        context['token'] = self.auth_token
        return context
    

class DatasetListViewSet(AuthenticatedViewSet):
    filter_class = None
    model_class = None
   
    def get_queryset(self):
        return self.model_class.viewable_instances_for_user(self.user)
    
    def get_object(self):
        urn = self.kwargs.get('urn', None)
        if urn is not None and self.model_class.objects.filter(urn=urn).count():
            instance = self.model_class.objects.filter(urn=urn).first()
            check_permission(instance, self.user)
        return super().get_object()


class ExperimentSetViewset(DatasetListViewSet):
    serializer_class = ExperimentSetSerializer
    filter_class = filters.ExperimentSetFilterModel
    model_class = models.experimentset.ExperimentSet
    queryset = models.experimentset.ExperimentSet.objects.all()
    lookup_field = 'urn'


class ExperimentViewset(DatasetListViewSet):
    serializer_class = ExperimentSerializer
    filter_class = filters.ExperimentFilter
    model_class = models.experiment.Experiment
    queryset = models.experiment.Experiment.objects.all()
    lookup_field = 'urn'


class ScoreSetViewset(DatasetListViewSet):
    serializer_class = ScoreSetSerializer
    filter_class = filters.ScoreSetFilter
    model_class = models.scoreset.ScoreSet
    queryset = models.scoreset.ScoreSet.objects.all()
    lookup_field = 'urn'


class UserViewset(AuthenticatedViewSet):
    queryset = User.objects.exclude(username='AnonymousUser')
    serializer_class = UserSerializer
    filter_class = UserFilter
    lookup_field = 'username'
   

# File download FBVs
# --------------------------------------------------------------------------- #
def validate_request(request, urn):
    try:
        if not ScoreSet.objects.filter(urn=urn).count():
            raise exceptions.NotFound()
        # Above passed so object should exist.
        user, token = authenticate(request)
        instance = ScoreSet.objects.get(urn=urn)
        check_permission(instance, user)
        return instance
    except (exceptions.PermissionDenied, exceptions.NotFound,
            exceptions.AuthenticationFailed) as e:
        return JsonResponse({'detail': e.detail}, status=e.status_code)


@cache_page(60 * 15)  # 15 minute cache
def scoreset_score_data(request, urn):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = \
        'attachment; filename="{}_scores.csv"'.format(urn)

    instance_or_response = validate_request(request, urn)
    if not isinstance(instance_or_response, ScoreSet):
        return instance_or_response

    scoreset = instance_or_response
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

    instance_or_response = validate_request(request, urn)
    if not isinstance(instance_or_response, ScoreSet):
        return instance_or_response
    
    scoreset = instance_or_response
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
    instance_or_response = validate_request(request, urn)
    if not isinstance(instance_or_response, ScoreSet):
        return instance_or_response

    scoreset = instance_or_response
    return JsonResponse(scoreset.extra_metadata, status=200)
