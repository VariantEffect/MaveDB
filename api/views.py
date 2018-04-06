from django.contrib.auth import get_user_model
from django.http import Http404
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404

from accounts.permissions import (
    user_is_anonymous, PermissionTypes
)

from dataset.models.experimentset import ExperimentSet
from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet
import dataset.constants as constants

from .serializers import (
    UserSerializer,
    ExperimentSetSerializer,
    ExperimentSerializer,
    ScoreSetSerializer
)


User = get_user_model()


# Users
# -------------------------------------------------------------------- #
def users_all(request):
    serializer = UserSerializer()
    users = [
        user for user in User.objects.all()
        if not (user_is_anonymous(user) or user.is_superuser)
    ]
    data = serializer.serialize_set(users)
    return JsonResponse(data)


def user_by_username(request, username):
    try:
        user = get_object_or_404(User, username=username)
    except Http404:
        response = render(
            request=request,
            template_name="main/404_not_found.html"
        )
        response.status_code = 404
        return response

    serializer = UserSerializer()
    data = serializer.serialize(user.pk)
    return JsonResponse(data)


# ExperimentSets
# -------------------------------------------------------------------- #
def experimentset_all(request):
    serializer = ExperimentSetSerializer()
    objects = ExperimentSet.objects.filter(private=False)
    data = serializer.serialize_set(objects)
    return JsonResponse(data)


def experimentset_by_urn(request, urn):
    try:
        obj = get_object_or_404(ExperimentSet, urn=urn)
        if obj.private:
            raise Http404()
    except Http404:
        response = render(
            request=request,
            template_name="main/404_not_found.html"
        )
        response.status_code = 404
        return response

    serializer = ExperimentSetSerializer()
    data = serializer.serialize(obj.pk)
    return JsonResponse(data)


# Experiments
# -------------------------------------------------------------------- #
def experiments_all(request):
    serializer = ExperimentSerializer()
    objects = Experiment.objects.filter(private=False)
    data = serializer.serialize_set(objects)
    return JsonResponse(data)


def experiment_by_urn(request, urn):
    try:
        obj = get_object_or_404(Experiment, urn=urn)
        if obj.private:
            raise Http404()
    except Http404:
        response = render(
            request=request,
            template_name="main/404_not_found.html"
        )
        response.status_code = 404
        return response

    serializer = ExperimentSerializer()
    data = serializer.serialize(obj.pk)
    return JsonResponse(data)


# Scoresets
# -------------------------------------------------------------------- #
def scoresets_all(request):
    serializer = ScoreSetSerializer()
    objects = ScoreSet.objects.filter(private=False)
    data = serializer.serialize_set(objects)
    return JsonResponse(data)


def scoreset_by_urn(request, urn):
    try:
        obj = get_object_or_404(ScoreSet, urn=urn)
        if obj.private:
            raise Http404()
    except Http404:
        response = render(
            request=request,
            template_name="main/404_not_found.html"
        )
        response.status_code = 404
        return response

    serializer = ScoreSetSerializer()
    data = serializer.serialize(obj.pk)
    return JsonResponse(data)


def download_variant_data(request, urn, dataset_column):
    """
    This view returns the variant dataset in csv format for a specific
    `ScoreSet`. This will either be the 'scores' or 'counts' dataset, which
    are the only two supported keys in a scoreset's `dataset_columns`
    attributes.

    Parameters
    ----------
    urn : `str`
        The `ScoreSet` urn which will be queried.

    dataset_column : `str`, choice: {'score_columns', 'count_columns', 'metadata_columns'}
        The type of dataset requested.

    Returns
    -------
    `StreamingHttpResponse`
        A stream is returned to handle the case where the data is too large
        to send all at once.
    """
    if dataset_column not in constants.valid_dataset_columns:
        raise ValueError("{} is not a valid variant data key.".format(
            dataset_column))
    try:
        scoreset = get_object_or_404(ScoreSet, urn=urn)
        has_permission = request.user.has_perm(
            PermissionTypes.CAN_VIEW, scoreset)

        if scoreset.private and not has_permission:
            response = render(
                request=request,
                template_name="main/403_forbidden.html",
                context={"instance": scoreset},
            )
            response.status_code = 403
            return response

    except Http404:
        response = render(
            request=request,
            template_name="main/404_not_found.html"
        )
        response.status_code = 404
        return response

    if dataset_column == constants.count_columns and \
            not scoreset.has_count_dataset:
        return StreamingHttpResponse("", content_type='text')

    if dataset_column == constants.metadata_columns and \
            not scoreset.has_metadata:
        return StreamingHttpResponse("", content_type='text')

    variants = scoreset.children.order_by("urn")
    columns = [constants.hgvs_column] + scoreset.dataset_columns[dataset_column]
    variant_column = constants.scoreset_to_variant_column[dataset_column]

    def gen_repsonse():
        yield ','.join(columns) + '\n'
        for var in variants:
            data = []
            for column_key in columns:
                if column_key == constants.hgvs_column:
                    data.append('"{}"'.format(var.hgvs))
                else:
                    data.append(str(var.data[variant_column][column_key]))
            yield ','.join(data) + '\n'

    return gen_repsonse()


def scoreset_score_data(request, urn):
    response = download_variant_data(
        request, urn, dataset_column=constants.score_columns)
    return StreamingHttpResponse(response, content_type='text')


def scoreset_count_data(request, urn):
    response = download_variant_data(
        request, urn, dataset_column=constants.count_columns)
    return StreamingHttpResponse(response, content_type='text')

def scoreset_metadata(request, urn):
    response = download_variant_data(
        request, urn, dataset_column=constants.metadata_columns)
    return StreamingHttpResponse(response, content_type='text')