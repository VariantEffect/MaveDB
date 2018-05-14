from rest_framework.viewsets import ReadOnlyModelViewSet

from django.contrib.auth import get_user_model
from django.http import Http404
from django.http import StreamingHttpResponse, JsonResponse
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

    scoreset = get_object_or_404(ScoreSet, urn=urn)
    has_permission = request.user.has_perm(PermissionTypes.CAN_VIEW, scoreset)
    if scoreset.private and not has_permission:
        raise Http404()

    if dataset_column == constants.score_columns and \
            not scoreset.has_score_dataset:
        return StreamingHttpResponse("", content_type='text')

    if dataset_column == constants.count_columns and \
            not scoreset.has_count_dataset:
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
    scoreset = get_object_or_404(ScoreSet, urn=urn)
    has_permission = request.user.has_perm(PermissionTypes.CAN_VIEW, scoreset)
    if scoreset.private and not has_permission:
        raise Http404()
    return JsonResponse(scoreset.extra_metadata)
