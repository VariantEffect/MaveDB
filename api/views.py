from rest_framework import viewsets

from django.contrib.auth import get_user_model
from django.http import Http404
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404

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

from .mixins import DatasetModelFilterMixin

User = get_user_model()


class DatasetModelViewSet(DatasetModelFilterMixin,
                          viewsets.ReadOnlyModelViewSet):

    def get_queryset(self, use_list=True):
        queryset = super().get_queryset()
        questions = self.make_q_object_list()
        q = self.join_func(questions)
        return queryset.filter(q)

    def list(self, request, *args, **kwargs):
        return_list = False
        if 'return_list' in kwargs:
            return_list = kwargs.pop('return_list')
        if return_list:
            return [i.urn for i in self.get_queryset()]
        else:
            return super().list(request, *args, **kwargs)


class ExperimentSetViewset(DatasetModelViewSet):
    queryset = ExperimentSet.objects.filter(private=False)
    serializer_class = ExperimentSetSerializer
    lookup_field = 'urn'


class ExperimentViewset(DatasetModelViewSet):
    queryset = Experiment.objects.filter(private=False)
    serializer_class = ExperimentSerializer
    lookup_field = 'urn'

    def filter_targets(self, query_key=None):
        field_name = 'scoresets__target__name'
        filter_type = 'iexact'
        query_key = query_key or 'target'
        return self.search_to_q(query_key, field_name, filter_type)

    def make_q_object_list(self):
        questions = super().make_q_object_list()
        questions += [self.filter_targets(self.key)]
        return questions


class ScoreSetViewset(DatasetModelViewSet):
    queryset = ScoreSet.objects.filter(private=False)
    serializer_class = ScoreSetSerializer
    lookup_field = 'urn'

    def filter_organism(self, query_key=None):
        field_name = 'target__reference_maps__genome__species_name'
        filter_type = 'iexact'
        query_key = query_key or 'organism'
        return self.search_to_q(query_key, field_name, filter_type)

    def filter_target(self, query_key=None):
        field_name = 'target__name'
        filter_type = 'iexact'
        query_key = query_key or 'target'
        return self.search_to_q(query_key, field_name, filter_type)

    def filter_target_sequence(self, query_key=None):
        field_name = 'target__wt_sequence__sequence'
        filter_type = 'iexact'
        query_key = query_key or 'sequence'
        return self.search_to_q(query_key, field_name, filter_type)

    def filter_reference_genome(self, query_key=None):
        field_name = 'target__reference_maps__genome__short_name'
        filter_type = 'iexact'
        query_key = query_key or 'reference'
        return self.search_to_q(query_key, field_name, filter_type)

    def filter_reference_genome_identifier(self, query_key=None):
        field_name_1 = 'target__reference_maps__genome__refseq_id__identifier'
        field_name_2 = 'target__reference_maps__genome__ensembl_id__identifier'
        filter_type = 'iexact'
        query_key = query_key or 'reference_accession'
        return self.or_join_qs([
            self.search_to_q(query_key, field_name_1, filter_type),
            self.search_to_q(query_key, field_name_2, filter_type),
        ])

    def filter_target_uniprot(self, query_key=None):
        field_name = 'target__uniprot_id__identifier'
        filter_type = 'iexact'
        query_key = query_key or 'uniprot'
        return self.search_to_q(query_key, field_name, filter_type)

    def filter_target_refseq(self, query_key=None):
        field_name = 'target__refseq_id__identifier'
        filter_type = 'iexact'
        query_key = query_key or 'refseq'
        return self.search_to_q(query_key, field_name, filter_type)

    def filter_target_ensembl(self, query_key=None):
        field_name = 'target__ensembl_id__identifier'
        filter_type = 'iexact'
        query_key = query_key or 'ensembl'
        return self.search_to_q(query_key, field_name, filter_type)

    def make_q_object_list(self):
        questions = super().make_q_object_list()
        questions += [
            self.filter_organism(self.key),
            self.filter_target(self.key),
            self.filter_target_sequence(self.key),
            self.filter_reference_genome(self.key),
            self.filter_reference_genome_identifier(self.key),
            self.filter_target_uniprot(self.key),
            self.filter_target_ensembl(self.key),
            self.filter_target_refseq(self.key),
        ]
        return questions


class UserViewset(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.exclude(username='AnonymousUser')
    serializer_class = UserSerializer
    lookup_field = 'username'


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
    if scoreset.private:
        raise Http404()

    if dataset_column == constants.score_columns and \
            not scoreset.has_score_dataset:
        return StreamingHttpResponse("", content_type='text')

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
