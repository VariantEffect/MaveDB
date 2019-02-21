import csv
import re
from datetime import datetime

from rest_framework import viewsets, exceptions

from django.contrib.auth import get_user_model
from django.http import HttpResponse, JsonResponse

from accounts.models import AUTH_TOKEN_RE, Profile
from accounts.filters import UserFilter
from accounts.serializers import UserSerializer

from metadata import models as meta_models
from metadata import serializers as meta_serializers

from genome import models as genome_models
from genome import serializers as genome_serializers

from dataset.templatetags.dataset_tags import filter_visible

from dataset import models, filters, constants
from dataset.serializers import (
    ExperimentSetSerializer,
    ExperimentSerializer,
    ScoreSetSerializer,
)

User = get_user_model()
ScoreSet = models.scoreset.ScoreSet


words_re = re.compile(r"\w+|[^\w\s]", flags=re.IGNORECASE)


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
        has_perm = user in instance.contributors
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
        return filter_visible(self.queryset, user=self.user)
    
    def get_object(self):
        urn = self.kwargs.get('urn', None)
        if urn is not None and \
                self.model_class.objects.filter(urn=urn).count():
            instance = self.model_class.objects.filter(urn=urn).first()
            check_permission(instance, self.user)
        return super().get_object()


class ExperimentSetViewset(DatasetListViewSet):
    http_method_names = ('get',)
    serializer_class = ExperimentSetSerializer
    filter_class = filters.ExperimentSetFilterModel
    model_class = models.experimentset.ExperimentSet
    queryset = models.experimentset.ExperimentSet.objects.all()
    lookup_field = 'urn'


class ExperimentViewset(DatasetListViewSet):
    http_method_names = ('get',)
    serializer_class = ExperimentSerializer
    filter_class = filters.ExperimentFilter
    model_class = models.experiment.Experiment
    queryset = models.experiment.Experiment.objects.all()
    lookup_field = 'urn'


class ScoreSetViewset(DatasetListViewSet):
    http_method_names = ('get',)
    serializer_class = ScoreSetSerializer
    filter_class = filters.ScoreSetFilter
    model_class = models.scoreset.ScoreSet
    queryset = models.scoreset.ScoreSet.objects.all()
    lookup_field = 'urn'


class UserViewset(AuthenticatedViewSet):
    http_method_names = ('get', )
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_class = UserFilter
    lookup_field = 'username'
   

# File download FBVs
# --------------------------------------------------------------------------- #
def validate_request(request, urn):
    """
    Validates an incoming request using the token in the auth header or checks
    session authentication. Also checks if urn exists.

    Returns JSON response on any error.

    Parameters
    ----------
    request : object
        Incoming request object.
    urn : str
        URN of the scoreset.

    Returns
    -------
    `JsonResponse`
    """
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


def format_csv_rows(variants, columns, dtype):
    """
    Formats each variant into a dictionary row containing the keys specified
    in `columns`.

    Parameters
    ----------
    variants : list[variant.models.Variant`]
        List of variants.
    columns : list[str]
        Columns to serialize.
    dtype : str, {'scores', 'counts'}
        The type of data requested. Either the 'score_data' or 'count_data'.

    Returns
    -------
    list[dict]
    """
    rowdicts = []
    for variant in variants:
        data = {}
        for column_key in columns:
            if column_key == constants.hgvs_nt_column:
                data[column_key] = str(variant.hgvs_nt)
            elif column_key == constants.hgvs_pro_column:
                data[column_key] = str(variant.hgvs_pro)
            elif column_key == 'accession':
                data[column_key] = str(variant.urn)
            else:
                data[column_key] = str(variant.data[dtype][column_key])
        rowdicts.append(data)
    return rowdicts


def urn_number(variant):
    number = variant.urn.split('#')[-1]
    if not str.isdigit(number):
        return 0
    return int(number)
    

def format_policy(policy, line_wrap_len=77):
    if not policy:
        policy = "Not specified"
    words = words_re.findall(policy)
    lines = []
    index = 0
    line = ""
    while index < len(words):
        if len(words[index]) == 1:
            new_line = '{}{}'.format(line, words[index])
        else:
            new_line = '{} {}'.format(line, words[index])
        if len(new_line) >= line_wrap_len:
            lines.append("# {}\n".format(line.strip()))
            line = ""
        else:
            line = new_line
            index += 1
    if line:
        lines.append("# {}\n".format(line.strip()))
    return lines
    

def format_response(response, scoreset, dtype):
    """
    Writes the CSV response by formatting each variant into a row including
    the columns `hgvs_nt`, `hgvs_pro`, `urn` and other uploaded columns.

    Parameters
    ----------
    response : `HttpResponse`
        Reponse object to write to.
    scoreset : `dataset.models.scoreset.ScoreSet`
        The scoreset requested.
    dtype : str
        The type of data requested. Either 'scores' or 'counts'.

    Returns
    -------
    `HttpResponse`
    """
    response.writelines([
        "# Accession: {}\n".format(scoreset.urn),
        "# Downloaded (UTC): {}\n".format(datetime.utcnow()),
        "# Licence: {}\n".format(scoreset.licence.long_name),
        "# Licence URL: {}\n".format(scoreset.licence.link),
    ])
    
    # Append data usage policy
    if scoreset.data_usage_policy is not None and \
            scoreset.data_usage_policy.strip():
        policy = "Data usage policy: {}".format(
            scoreset.data_usage_policy.strip())
        lines = format_policy(policy)
        response.writelines(lines)

    variants = sorted(
        scoreset.children.all(), key=lambda v: urn_number(v))
        
    if dtype == 'scores':
        columns = ['accession', ] + scoreset.score_columns
        type_column = constants.variant_score_data
    elif dtype == 'counts':
        columns = ['accession', ] + scoreset.count_columns
        type_column = constants.variant_count_data
    else:
        raise ValueError(
            "Unknown variant dtype {}. Expected "
            "either 'scores' or 'counts'.".format(dtype))

    # 'hgvs_nt', 'hgvs_pro', 'urn' are present by default, hence <= 2
    if not variants or len(columns) <= 3:
        return response

    rows = format_csv_rows(variants, columns=columns, dtype=type_column)
    writer = csv.DictWriter(
        response, fieldnames=columns, quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    writer.writerows(rows)
    return response


def scoreset_score_data(request, urn):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = \
        'attachment; filename="{}_scores.csv"'.format(urn)
    scoreset = validate_request(request, urn)
    if not isinstance(scoreset, ScoreSet):
        return scoreset  # Invalid request, return response.
    return format_response(response, scoreset, dtype='scores')


def scoreset_count_data(request, urn):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = \
        'attachment; filename="{}_counts.csv"'.format(urn)
    scoreset = validate_request(request, urn)
    if not isinstance(scoreset, ScoreSet):
        return scoreset  # Invalid request, return response.
    return format_response(response, scoreset, dtype='counts')


def scoreset_metadata(request, urn):
    instance_or_response = validate_request(request, urn)
    if not isinstance(instance_or_response, ScoreSet):
        return instance_or_response
    scoreset = instance_or_response
    return JsonResponse(scoreset.extra_metadata, status=200)


# ----- Other API endpoints
class KeywordViewSet(viewsets.ModelViewSet):
    http_method_names = ('get', )
    queryset = meta_models.Keyword.objects.all()
    serializer_class = meta_serializers.KeywordSerializer


class PubmedIdentifierViewSet(viewsets.ModelViewSet):
    http_method_names = ('get', )
    queryset = meta_models.PubmedIdentifier.objects.all()
    serializer_class = meta_serializers.PubmedIdentifierSerializer
    
    
class SraIdentifierViewSet(viewsets.ModelViewSet):
    http_method_names = ('get', )
    queryset = meta_models.SraIdentifier.objects.all()
    serializer_class = meta_serializers.SraIdentifierSerializer
    
    
class DoiIdentifierViewSet(viewsets.ModelViewSet):
    http_method_names = ('get', )
    queryset = meta_models.DoiIdentifier.objects.all()
    serializer_class = meta_serializers.DoiIdentifierSerializer
    
    
class EnsemblIdentifierViewSet(viewsets.ModelViewSet):
    http_method_names = ('get', )
    queryset = meta_models.EnsemblIdentifier.objects.all()
    serializer_class = meta_serializers.EnsemblIdentifierSerializer


class RefseqIdentifierViewSet(viewsets.ModelViewSet):
    http_method_names = ('get',)
    queryset = meta_models.RefseqIdentifier.objects.all()
    serializer_class = meta_serializers.RefseqIdentifierSerializer
    
    
class UniprotIdentifierViewSet(viewsets.ModelViewSet):
    http_method_names = ('get',)
    queryset = meta_models.UniprotIdentifier.objects.all()
    serializer_class = meta_serializers.UniprotIdentifierSerializer
    
    
class GenomeIdentifierViewSet(viewsets.ModelViewSet):
    http_method_names = ('get',)
    queryset = meta_models.GenomeIdentifier.objects.all()
    serializer_class = meta_serializers.GenomeIdentifierSerializer
    
    
class TargetGeneViewSet(viewsets.ModelViewSet):
    http_method_names = ('get',)
    queryset = genome_models.TargetGene.objects.exclude(
        scoreset__private=True
    )
    serializer_class = genome_serializers.TargetGeneSerializer
    
    
class ReferenceGenomeViewSet(viewsets.ModelViewSet):
    http_method_names = ('get',)
    queryset = genome_models.ReferenceGenome.objects.all()
    serializer_class = genome_serializers.ReferenceGenomeSerializer
