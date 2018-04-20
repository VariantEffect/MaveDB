import logging

from core.mixins import SearchMixin
logger = logging.getLogger('django')



class DatasetModelSearchMixin(SearchMixin):
    """
    Filter :class:`DatasetModel` instances by common fields:

        'urn': 'urn',
        'abstract': 'abstract_text',
        'method': 'method_text',
        'title': 'title',
        'description': 'short_description',
        'keywords': 'keywords',
        'sra': 'sra_ids__identifier',
        'doi': 'doi_ids__identifier',
        'pubmed': 'pubmed_ids__identifier',

    Expects the above :class:`DatasetModel` field names to work correctly.
    """
    @staticmethod
    def search_field_to_model_field():
        return {
            'urn': 'urn',
            'abstract': 'abstract_text',
            'method': 'method_text',
            'title': 'title',
            'description': 'short_description',
            'keywords': 'keywords',
            'sra': 'sra_ids__identifier',
            'doi': 'doi_ids__identifier',
            'pubmed': 'pubmed_ids__identifier',
        }

    def search_field_to_function(self):
        return {
            'abstract': self.filter_abstract,
            'method': self.filter_method,
            'title': self.filter_title,
            'description': self.filter_description,
            'keywords': self.filter_keywords,
            'sra': self.filter_sra,
            'doi': self.filter_doi,
            'pubmed': self.filter_pubmed,
            'urn': self.filter_urn,
        }

    def filter_abstract(self, value):
        return self.search_to_q(
            value, field_name='abstract_text', filter_type='icontains')

    def filter_method(self, value):
        return self.search_to_q(
            value, field_name='method_text', filter_type='icontains')

    def filter_title(self, value):
        return self.search_to_q(
            value, field_name='title', filter_type='icontains')

    def filter_description(self, value):
        return self.search_to_q(
            value, field_name='short_description', filter_type='icontains')

    def filter_keywords(self, value):
        return self.search_to_q(
            value, field_name='short_description', filter_type='icontains')

    def filter_sra(self, value):
        return self.search_to_q(
            value, field_name='sra_ids__identifier', filter_type='iexact')

    def filter_doi(self, value):
        return self.search_to_q(
            value, field_name='doi_ids__identifier', filter_type='iexact')

    def filter_pubmed(self, value):
        return self.search_to_q(
            value, field_name='pubmed_ids__identifier', filter_type='iexact')

    def filter_urn(self, value):
        return self.search_to_q(
            value, field_name='urn', filter_type='iexact')


class ExperimentSetSearchMixin(DatasetModelSearchMixin):
    """
    Filter :class:`ExperimentSet` instances by common fields:

        'urn': 'urn',
        'abstract': 'abstract_text',
        'method': 'method_text',
        'title': 'title',
        'description': 'short_description',
        'keywords': 'keywords',
        'sra': 'sra_ids__identifier',
        'doi': 'doi_ids__identifier',
        'pubmed': 'pubmed_ids__identifier',

    Expects the above :class:`ExperimentSet` field names to work correctly.
    """
    @staticmethod
    def search_field_to_model_field():
        dict_ = super().search_field_to_model_field()
        return dict_

    def search_field_to_function(self):
        dict_ = super().search_field_to_function()
        return dict_


class ExperimentSearchMixin(DatasetModelSearchMixin):
    """
    Filter :class:`Experiment` instances by common fields in
    :class:`DatasetModelSearchMixin` and the below:

        'target': 'scoresets__target__name'

    Expects the above :class:`Experiment` field names to work correctly.
    """
    @staticmethod
    def search_field_to_model_field():
        dict_ = super().search_field_to_model_field()
        dict_.update({
            'target': 'scoresets__target__name'
        })
        return dict_

    def search_field_to_function(self):
        dict_ = super().search_field_to_function()
        dict_.update({
            'target': self.filter_target
        })
        return dict_

    def filter_target(self, value):
        field_name = 'scoresets__target__name'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)


class ScoreSetSearchMixin(DatasetModelSearchMixin):
    """
    Filter :class:`ScoreSet` instances by common fields in
    :class:`DatasetModelSearchMixin` and the below:

        'target': 'target__name',
        'organism': 'target__reference_maps__genome__species_name',
        'sequence': 'target__wt_sequence__sequence',
        'reference': [
            'target__reference_maps__genome__short_name',
            'target__reference_maps__genome__refseq_id__identifier',
            'target__reference_maps__genome__ensembl_id__identifier',
        ],
        'uniprot': 'target__uniprot_id__identifier',
        'ensembl': 'target__ensembl_id__identifier',
        'refseq': 'target__refseq_id__identifier',

    Expects the above :class:`ScoreSet` field names to work correctly.
    """

    @staticmethod
    def search_field_to_model_field():
        dict_ = super().search_field_to_model_field()
        dict_.update({
            'target': 'target__name',
            'organism': 'target__reference_maps__genome__species_name',
            'sequence': 'target__wt_sequence__sequence',
            'reference': [
                'target__reference_maps__genome__short_name',
                'target__reference_maps__genome__refseq_id__identifier',
                'target__reference_maps__genome__ensembl_id__identifier',
            ],
            'uniprot': 'target__uniprot_id__identifier',
            'ensembl': 'target__ensembl_id__identifier',
            'refseq': 'target__refseq_id__identifier',
        })
        return dict_

    def search_field_to_function(self):
        dict_ = super().search_field_to_function()
        dict_.update({
            'organism': self.filter_organism,
            'target': self.filter_target,
            'sequence': self.filter_target_sequence,
            'reference': self.filter_reference_genome,
            'uniprot': self.filter_target_uniprot,
            'ensembl': self.filter_target_ensembl,
            'refseq': self.filter_target_refseq,
        })
        return dict_
    
    def filter_organism(self, value):
        field_name = 'target__reference_maps__genome__species_name'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)

    def filter_target(self, value):
        field_name = 'target__name'
        filter_type = 'iexact'
        value = value or 'target'
        return self.search_to_q(value, field_name, filter_type)

    def filter_target_sequence(self, value):
        field_name = 'target__wt_sequence__sequence'
        filter_type = 'iexact'
        value = value or 'sequence'
        return self.search_to_q(value, field_name, filter_type)

    def filter_reference_genome(self, value):
        field_name_1 = 'target__reference_maps__genome__short_name'
        field_name_2 = 'target__reference_maps__genome__refseq_id__identifier'
        field_name_3 = 'target__reference_maps__genome__ensembl_id__identifier'
        filter_type = 'iexact'
        return self.or_join_qs([
            self.search_to_q(value, field_name_1, filter_type),
            self.search_to_q(value, field_name_2, filter_type),
            self.search_to_q(value, field_name_3, filter_type),
        ])

    def filter_target_uniprot(self, value):
        field_name = 'target__uniprot_id__identifier'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)

    def filter_target_refseq(self, value):
        field_name = 'target__refseq_id__identifier'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)

    def filter_target_ensembl(self, value):
        field_name = 'target__ensembl_id__identifier'
        filter_type = 'iexact'
        return self.search_to_q(value, field_name, filter_type)
