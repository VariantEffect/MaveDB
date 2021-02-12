import csv
import json
import logging
import re
from datetime import datetime
from reversion import create_revision

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from rest_framework import exceptions, parsers, status, views, viewsets
from rest_framework.response import Response

from accounts.filters import UserFilter
from accounts.models import AUTH_TOKEN_RE, Profile
from accounts.serializers import UserSerializer
from core.utilities import is_null
from dataset import models, filters, constants
from dataset.forms.scoreset import ScoreSetForm
from dataset.mixins import DatasetPermissionMixin
from dataset.models.experiment import Experiment
from dataset.serializers import (
    ExperimentSetSerializer,
    ExperimentSerializer,
    ScoreSetSerializer,
)
from dataset.tasks import create_variants
from dataset.templatetags.dataset_tags import filter_visible
from genome import models as genome_models, serializers as genome_serializers
from genome.forms import PrimaryReferenceMapForm, TargetGeneForm
from main.models import Licence
from metadata import models as meta_models, serializers as meta_serializers
from metadata.forms import (
    UniprotOffsetForm,
    EnsemblOffsetForm,
    RefseqOffsetForm,
)

User = get_user_model()
ScoreSet = models.scoreset.ScoreSet
logger = logging.getLogger("django")

words_re = re.compile(r"\w+|[^\w\s]", flags=re.IGNORECASE)


def authenticate(request):
    user, token = None, request.META.get("HTTP_AUTHORIZATION", None)
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
        if instance.is_meta_analysis:
            metas = getattr(
                instance, "meta_analysis_scoresets", ScoreSet.objects.none()
            )
            can_access_at_least_one_meta_scoreset = any(
                user.has_perm(DatasetPermissionMixin.VIEW_PERMISSION, s)
                for s in metas
            )
            return can_access_at_least_one_meta_scoreset
        else:
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
        except (
            exceptions.AuthenticationFailed,
            exceptions.PermissionDenied,
            exceptions.NotFound,
        ) as e:
            return JsonResponse({"detail": e.detail}, status=e.status_code)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["user"] = self.user
        context["token"] = self.auth_token
        return context


class DatasetListViewSet(AuthenticatedViewSet):
    filter_class = None
    model_class = None

    def get_queryset(self):
        return filter_visible(self.queryset.all(), user=self.user)

    def get_object(self):
        urn = self.kwargs.get("urn", None)
        if (
            urn is not None
            and self.model_class.objects.filter(urn=urn).count()
        ):
            instance = self.model_class.objects.filter(urn=urn).first()
            check_permission(instance, self.user)
        return super().get_object()


class ExperimentSetViewset(DatasetListViewSet):
    http_method_names = ("get",)
    serializer_class = ExperimentSetSerializer
    filter_class = filters.ExperimentSetFilterModel
    model_class = models.experimentset.ExperimentSet
    queryset = models.experimentset.ExperimentSet.objects.all()
    lookup_field = "urn"


class ExperimentViewset(DatasetListViewSet):
    http_method_names = ("get",)
    serializer_class = ExperimentSerializer
    filter_class = filters.ExperimentFilter
    model_class = models.experiment.Experiment
    queryset = models.experiment.Experiment.objects.all()
    lookup_field = "urn"

class ScoreSetViewset(DatasetListViewSet):
    http_method_names = ("get", 'post',)
    serializer_class = ScoreSetSerializer
    filter_class = filters.ScoreSetFilter
    model_class = models.scoreset.ScoreSet
    queryset = models.scoreset.ScoreSet.objects.all()
    lookup_field = "urn"

    parser_classes = (parsers.MultiPartParser, parsers.FormParser,)

    def create(self, request, format=None):
        """
        Format request.data into ScoreSetForm

        request.data : QueryDict
            request: JSON encoded as a string
                short_description : str
                title : str
                experiment : dataset.models.experiment.Experiment.pk (str?)

                score_data : InMemoryUploadedFile
                count_data : InMemoryUploadedFile
                meta_data : InMemoryUploadedFile
        """
        ### COPIED (then modified) FROM dataset/views/scoreset.py
        # TODO: move all copied logic into serializers and out of both views
        def submit_job(form: ScoreSetForm, object: ScoreSet, user):
            if form.has_variants() and object.private:
                logger.info(
                    f"Submitting task from {user} for {object.urn} to Celery."
                )

                object.processing_state = constants.processing
                object.save()

                scores_rs, counts_rs, index = form.serialize_variants()
                task_kwargs = {
                    "user_pk": user.pk,
                    "scoreset_urn": object.urn,
                    "scores_records": scores_rs,
                    "counts_records": counts_rs,
                    "dataset_columns": form.dataset_columns.copy(),
                    "index": index,
                }

                success, _ = create_variants.submit_task(
                    kwargs=task_kwargs,
                )

                logger.info(
                    "Submission to celery from {} for {}: {}".format(
                        user, object.urn, success
                    )
                )

                if not success:
                    object.processing_state = constants.failed
                    object.save()

        @transaction.atomic()
        def save_forms(forms, user):
            scoreset_form: ScoreSetForm = forms['scoreset_form']

            with create_revision():
                scoreset: ScoreSet = scoreset_form.save(commit=True)
                object: ScoreSet = scoreset

            target_form: TargetGeneForm = forms['target_gene_form']
            reference_map_form: PrimaryReferenceMapForm = forms[
                'reference_map_form'
            ]
            uniprot_offset_form: UniprotOffsetForm = forms[
                'uniprot_offset_form'
            ]
            refseq_offset_form: RefseqOffsetForm = forms['refseq_offset_form']
            ensembl_offset_form: EnsemblOffsetForm = forms[
                'ensembl_offset_form'
            ]

            target: TargetGene = target_form.save(
                commit=True, scoreset=scoreset
            )

            reference_map_form.instance.target = target
            reference_map_form.save(commit=True)

            uniprot_offset = uniprot_offset_form.save(
                target=target,
                commit=True,
            )
            refseq_offset = refseq_offset_form.save(
                target=target,
                commit=True,
            )
            ensembl_offset = ensembl_offset_form.save(
                target=target,
                commit=True,
            )

            if uniprot_offset:
                target.uniprot_id = uniprot_offset.identifier
            else:
                target.uniprot_id = None

            if refseq_offset:
                target.refseq_id = refseq_offset.identifier
            else:
                target.refseq_id = None

            if ensembl_offset:
                target.ensembl_id = ensembl_offset.identifier
            else:
                target.ensembl_id = None

            target.save()

            object.add_administrators(user)
            transaction.on_commit(lambda: submit_job(
                form=scoreset_form, object=object, user=user
            ))
        ### END COPY

        def _fetch(needs_fetching, fetch_info):
            new_dict = {}
            for key in fetch_info.keys():
                if key not in needs_fetching:
                    raise ValueError(f"Payload did not contain needed key {key}.")
                if needs_fetching[key] is None:
                    continue
                # Make a case-insensitive match by formatting the get key as
                # KEY__iexact when fetching
                get_field = fetch_info[key]['get_field']
                fetch_iexact_key = f"{get_field}__iexact"
                get_dict = {fetch_iexact_key: needs_fetching[key][get_field]}
                new_dict[key] = fetch_info[key]['class'].objects.get(**get_dict).pk
            return new_dict

        def _parse_data(data, flat_keys, needs_fetching, fetch_info):
            to_return = {}
            for key in flat_keys:
                data_value = data.get(key, None)
                if not data_value:
                    continue
                to_return[key] = data_value
            to_return.update(_fetch(needs_fetching, fetch_info))
            return to_return

        def _parse_scoreset_data(data):
            flat_keys = [
                'title',
                'short_description',
                'abstract_text',
                'method_text',
                'keywords',
                'doi_ids',
                'sra_ids',
                'pubmed_ids',
                'meta_analysis_for',
                'data_usage_policy'
            ]
            needs_fetching = {
                'experiment': {
                    'urn': data.get('experiment', None)
                },
                'licence': data.get('licence', None),
                'replaces': data.get('replaces', None)
            }
            fetch_info = {
                'experiment': {
                    'class': Experiment,
                    'get_field': 'urn'
                },
                'licence': {
                    'class': Licence,
                    'get_field': 'short_name'
                },
                'replaces': {
                    'class': ScoreSet,
                    'get_field': 'urn'
                }
            }
            return _parse_data(data, flat_keys, needs_fetching, fetch_info)

        def _parse_target_data(data):
            # 'type' needs to transform to 'category'
            if 'type' in data:
                data['category'] = data['type']
            flat_keys = ['name', 'category', 'sequence_type', 'reference_sequence']
            return _parse_data(data, flat_keys, {}, {})

        def _parse_uniprot_data(data):
            needs_fetching = {
                'uniprot': data
            }
            fetch_info = {
                'uniprot': {
                    'class': meta_models.UniprotIdentifier,
                    'get_field': 'identifier'
                },
            }
            return _parse_data(data, [], needs_fetching, fetch_info)

        def _parse_ensembl_data(data):
            needs_fetching = {
                'ensembl': data
            }
            fetch_info = {
                'ensembl': {
                    'class': meta_models.EnsemblIdentifier,
                    'get_field': 'identifier'
                },
            }
            return _parse_data(data, [], needs_fetching, fetch_info)

        def _parse_refseq_data(data):
            needs_fetching = {
                'refseq': data
            }
            fetch_info = {
                'refseq': {
                    'class': meta_models.RefseqIdentifier,
                    'get_field': 'identifier'
                },
            }
            return _parse_data(data, [], needs_fetching, fetch_info)

        def _parse_reference_maps_data(data):
            needs_fetching = {}
            reference_maps = data if data else []
            for i in range(len(reference_maps)):
                '''
                'reference_maps': [
                    {
                        'KEY': {    # <- always only one key here, e.g. 'genome'
                            'short_name': 'VALUE'
                        }
                    }, ...
                ]
                '''
                # Right now, it looks like the only available key is 'genome'
                key = list(reference_maps[i].keys())[0] # <- this is the above key, 'genome'
                needs_fetching[key] = reference_maps[i][key]
            fetch_info = {
                'genome': {
                    'class': genome_models.ReferenceGenome,
                    'get_field': 'short_name'
                },
            }
            return _parse_data(data, [], needs_fetching, fetch_info)

        # Breakdown of the original request monolith
        user, _ = authenticate(request)
        request_data = json.loads(request.POST['request'])
        scoreset_request_data = request_data['scoreset']
        target_request_data = request_data['target']
        uniprot_request_data = request_data['uniprot']
        ensembl_request_data = request_data['ensembl']
        refseq_request_data = request_data['refseq']
        reference_maps_request_data = request_data['reference_maps']
        files = {
            constants.variant_score_data: request.FILES['score_data'],
            constants.variant_count_data: request.FILES['count_data'],
            constants.meta_data: request.FILES['meta_data'],
        }
        if 'fasta_file' in request.FILES:
            files['sequence_fasta'] = request.FILES['fasta_file']

        try:
            scoreset_data = _parse_scoreset_data(scoreset_request_data)
            target_data = _parse_target_data(target_request_data)
            uniprot_data = _parse_uniprot_data(uniprot_request_data)
            ensembl_data = _parse_ensembl_data(ensembl_request_data)
            refseq_data = _parse_refseq_data(refseq_request_data)
            reference_maps_data = _parse_reference_maps_data(reference_maps_request_data)
        except Exception as e:
            response_data = {
                'status': 'Bad request.',
                'message': 'Could not parse data correctly.',
                'parse_error': repr(e)
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Change this to be something where we get the user by the token request or something
            scoreset_form = ScoreSetForm(data=scoreset_data, files=files, user=user)
            target_form = TargetGeneForm(data=target_data, files=files, user=user)
            uniprot_form = UniprotOffsetForm(data=uniprot_data)
            ensembl_form = EnsemblOffsetForm(data=ensembl_data)
            refseq_form = RefseqOffsetForm(data=refseq_data)
            reference_map_form = PrimaryReferenceMapForm(data=reference_maps_data)
            # These keys need to match what lives in the save_forms logic above
            # which in turn was copied from dataset/views/scoreset, so let's
            # make it backwards compatible
            forms = {
                'scoreset_form': scoreset_form,
                'target_gene_form': target_form,
                'uniprot_offset_form': uniprot_form,
                'ensembl_offset_form': ensembl_form,
                'refseq_offset_form': refseq_form,
                'reference_map_form': reference_map_form,
            }
        except Exception as e:
            response_data = {
                'status': 'Bad request',
                'message': 'Could not create forms correctly with the given data.',
                'form_creation_error': repr(e)
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)


        ### COPIED (then modified) FROM dataset/views/scoreset.py
        # TODO: move all copied logic into serializers and out of both views
        valid = True
        valid &= target_form.is_valid()
        valid &= scoreset_form.is_valid(targetseq=target_form.get_targetseq())
        # Check that if AA sequence, dataset defined pro variants only.
        if (
            target_form.sequence_is_protein
            and not scoreset_form.allow_aa_sequence
        ):
            valid = False
            target_form.add_error(
                "sequence_text",
                "Protein sequences are allowed if your data set exclusively "
                "defines protein variants.",
            )
        ### END COPY

        form_errors = {}
        for key in forms.keys():
            if forms[key].errors:
                form_errors[f"{key}_errors"] = forms[key].errors.as_json()
        if form_errors:
            response_data = {
                'status': 'Bad request',
                'message': 'One or more forms were invalid.',
                'forms_invalid_error': form_errors
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            save_forms(forms=forms, user=user)
        except Exception as e:
            response_data = {
                'status': 'Bad request',
                'message': 'ScoreSet could not be created with the given data.',
                'scoreset_creation_error': repr(e)
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        return HttpResponse(status=204)


class UserViewset(AuthenticatedViewSet):
    http_method_names = ("get",)
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_class = UserFilter
    lookup_field = "username"


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
    except (
        exceptions.PermissionDenied,
        exceptions.NotFound,
        exceptions.AuthenticationFailed,
    ) as e:
        return JsonResponse({"detail": e.detail}, status=e.status_code)


def format_csv_rows(variants, columns, dtype, na_rep="NA"):
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
    na_rep : str
        String to represent null values.

    Returns
    -------
    list[dict]
    """
    rowdicts = []
    for variant in variants:
        data = {}
        for column_key in columns:
            if column_key == constants.hgvs_nt_column:
                value = str(variant.hgvs_nt)
            elif column_key == constants.hgvs_pro_column:
                value = str(variant.hgvs_pro)
            elif column_key == constants.hgvs_tx_column:
                value = str(variant.hgvs_tx)
            elif column_key == "accession":
                value = str(variant.urn)
            else:
                value = str(variant.data[dtype][column_key])
            if is_null(value):
                value = na_rep
            data[column_key] = value
        rowdicts.append(data)
    return rowdicts


def urn_number(variant):
    number = variant.urn.split("#")[-1]
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
            new_line = "{}{}".format(line, words[index])
        else:
            new_line = "{} {}".format(line, words[index])
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
    response.writelines(
        [
            "# Accession: {}\n".format(scoreset.urn),
            "# Downloaded (UTC): {}\n".format(datetime.utcnow()),
            "# Licence: {}\n".format(scoreset.licence.long_name),
            "# Licence URL: {}\n".format(scoreset.licence.link or str(None)),
        ]
    )

    # Append data usage policy
    if (
        scoreset.data_usage_policy is not None
        and scoreset.data_usage_policy.strip()
    ):
        policy = "Data usage policy: {}".format(
            scoreset.data_usage_policy.strip()
        )
        lines = format_policy(policy)
        response.writelines(lines)

    variants = sorted(scoreset.children.all(), key=lambda v: urn_number(v))

    if dtype == "scores":
        columns = ["accession"] + scoreset.score_columns
        type_column = constants.variant_score_data
    elif dtype == "counts":
        columns = ["accession"] + scoreset.count_columns
        type_column = constants.variant_count_data
    else:
        raise ValueError(
            "Unknown variant dtype {}. Expected "
            "either 'scores' or 'counts'.".format(dtype)
        )

    # 'hgvs_nt', 'hgvs_tx', 'hgvs_pro', 'urn' are present by default
    if not variants or len(columns) <= 4:
        return response

    rows = format_csv_rows(variants, columns=columns, dtype=type_column)
    writer = csv.DictWriter(
        response, fieldnames=columns, quoting=csv.QUOTE_MINIMAL
    )
    writer.writeheader()
    writer.writerows(rows)
    return response


def scoreset_score_data(request, urn):
    response = HttpResponse(content_type="text/csv")
    response[
        "Content-Disposition"
    ] = 'attachment; filename="{}_scores.csv"'.format(urn)
    scoreset = validate_request(request, urn)
    if not isinstance(scoreset, ScoreSet):
        return scoreset  # Invalid request, return response.
    return format_response(response, scoreset, dtype="scores")


def scoreset_count_data(request, urn):
    response = HttpResponse(content_type="text/csv")
    response[
        "Content-Disposition"
    ] = 'attachment; filename="{}_counts.csv"'.format(urn)
    scoreset = validate_request(request, urn)
    if not isinstance(scoreset, ScoreSet):
        return scoreset  # Invalid request, return response.
    return format_response(response, scoreset, dtype="counts")


def scoreset_metadata(request, urn):
    instance_or_response = validate_request(request, urn)
    if not isinstance(instance_or_response, ScoreSet):
        return instance_or_response
    scoreset = instance_or_response
    return JsonResponse(scoreset.extra_metadata, status=200)


# ----- Other API endpoints
class KeywordViewSet(viewsets.ModelViewSet):
    http_method_names = ("get",)
    queryset = meta_models.Keyword.objects.all()
    serializer_class = meta_serializers.KeywordSerializer


class PubmedIdentifierViewSet(viewsets.ModelViewSet):
    http_method_names = ("get",)
    queryset = meta_models.PubmedIdentifier.objects.all()
    serializer_class = meta_serializers.PubmedIdentifierSerializer


class SraIdentifierViewSet(viewsets.ModelViewSet):
    http_method_names = ("get",)
    queryset = meta_models.SraIdentifier.objects.all()
    serializer_class = meta_serializers.SraIdentifierSerializer


class DoiIdentifierViewSet(viewsets.ModelViewSet):
    http_method_names = ("get",)
    queryset = meta_models.DoiIdentifier.objects.all()
    serializer_class = meta_serializers.DoiIdentifierSerializer


class EnsemblIdentifierViewSet(viewsets.ModelViewSet):
    http_method_names = ("get",)
    queryset = meta_models.EnsemblIdentifier.objects.all()
    serializer_class = meta_serializers.EnsemblIdentifierSerializer


class RefseqIdentifierViewSet(viewsets.ModelViewSet):
    http_method_names = ("get",)
    queryset = meta_models.RefseqIdentifier.objects.all()
    serializer_class = meta_serializers.RefseqIdentifierSerializer


class UniprotIdentifierViewSet(viewsets.ModelViewSet):
    http_method_names = ("get",)
    queryset = meta_models.UniprotIdentifier.objects.all()
    serializer_class = meta_serializers.UniprotIdentifierSerializer


class GenomeIdentifierViewSet(viewsets.ModelViewSet):
    http_method_names = ("get",)
    queryset = meta_models.GenomeIdentifier.objects.all()
    serializer_class = meta_serializers.GenomeIdentifierSerializer


class TargetGeneViewSet(viewsets.ModelViewSet):
    http_method_names = ("get",)
    queryset = genome_models.TargetGene.objects.exclude(scoreset__private=True)
    serializer_class = genome_serializers.TargetGeneSerializer


class ReferenceGenomeViewSet(viewsets.ModelViewSet):
    http_method_names = ("get",)
    queryset = genome_models.ReferenceGenome.objects.all()
    serializer_class = genome_serializers.ReferenceGenomeSerializer
