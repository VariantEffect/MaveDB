import json
import django.forms as forms

from core.utilities import is_null

from main.models import Licence
from metadata.models import (
    Keyword,
    RefseqIdentifier,
    EnsemblIdentifier,
    UniprotIdentifier,
    GenomeIdentifier,
    SraIdentifier,
    DoiIdentifier,
    PubmedIdentifier,
)

from genome.models import ReferenceGenome, TargetGene

from dataset.mixins import ExperimentFilterMixin, ScoreSetFilterMixin


experiment_filter = ExperimentFilterMixin()
scoreset_filter = ScoreSetFilterMixin()


def passthrough(x):
    return x


def parse_char_list(value):
    if isinstance(value, (list, set, tuple)):
        return list(value)
    try:
        return json.loads(
            value
                .replace('[\'', '[\"')
                .replace('\']', '\"]')
                .replace(', \'', ', \"')
                .replace('\',', '\",')
        )
    except (ValueError, TypeError):
        return [value]


class FormFilterMixin:
    """Creates filters for experiments and scoresets."""
    def make_experiment_filters(self, join=True):
        return self.make_filters(join=join, filter_=experiment_filter)

    def make_scoreset_filters(self, join=True):
        return self.make_filters(join=join, filter_=scoreset_filter)
    

class MetadataSearchForm(forms.Form, FormFilterMixin):
    """Search by text fields and keywords."""
    title = forms.CharField(
        max_length=None, label="Title", required=False,
        help_text='Search entries by title.',
        widget=forms.widgets.TextInput()
    )

    description = forms.CharField(
        max_length=None, label="Description", required=False,
        help_text='Search entries by short description.',
        widget=forms.widgets.TextInput()
    )

    method_abstract = forms.CharField(
        max_length=None, label="Abstract/Method", required=False,
        help_text='Search entries by abstract/method.',
        widget=forms.widgets.TextInput()
    )

    licence = forms.CharField(
        label='Licence', required=False,
        help_text="Search for Score Sets with the selected licence type.",
        widget=forms.widgets.Select(),
    )

    def __init__(self, *args, **kwargs):
        super(MetadataSearchForm, self).__init__(*args, **kwargs)
        self.fields['keywords'] = forms.CharField(
            label='Keywords',
            help_text='Search by keywords.',
            required=False,
            widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.text, i.text)
                    for i in Keyword.objects.all()
                ]))
            ),
        )
        l_field = self.fields['licence']
        l_field.widget.choices = \
            [("", '--------')] + \
            [(i.long_name, i.long_name) for i in Licence.objects.all()]

    def clean_method_abstract(self):
        method_abtract = self.cleaned_data.get("method_abstract", "")
        if is_null(method_abtract):
            return ""
        return method_abtract

    def clean_description(self):
        description = self.cleaned_data.get("description", "")
        if is_null(description):
            return ""
        return description

    def clean_title(self):
        title = self.cleaned_data.get("title", "")
        if is_null(title):
            return ""
        return title

    def clean_keywords(self):
        field_name = 'keywords'
        instances = parse_char_list(self.cleaned_data.get(field_name, []))
        instances = list(set([i for i in instances if not is_null(i)]))
        return instances

    def make_filters(self, join=True, filter_=experiment_filter):
        data = self.cleaned_data
        abstract = {'abstract': data.get('method_abstract', "")}
        method = {'method': data.get('method_abstract', "")}
        title = {'title': data.get('title', "")}
        description = {'description': data.get('description', "")}
        keywords = {'keywords': data.get('keywords', [])}
        licence = {'licence': data.get('licence', "")}

        abstract_q = filter_.search_all(abstract, join_func=None)
        method_q = filter_.search_all(method, join_func=None)
        title_q = filter_.search_all(title, join_func=None)
        description_q = filter_.search_all(description, join_func=None)
        keywords_q = filter_.search_all(keywords, join_func=None)
        method_abstract_q = filter_.or_join_qs(abstract_q + method_q)
        licence_q = filter_.search_all(licence, join_func=None)

        if not len(method_abstract_q):
            method_abstract_q = []
        else:
            method_abstract_q = [method_abstract_q]
        qs = method_abstract_q + title_q + description_q + keywords_q + licence_q

        join_func = passthrough
        if join:
            join_func = filter_.and_join_qs
        return join_func(qs)


class MetaIdentifiersSearchForm(forms.Form, FormFilterMixin):
    """Search by PubMed, SRA and DOI."""

    def __init__(self, *args, **kwargs):
        super(MetaIdentifiersSearchForm, self).__init__(*args, **kwargs)
        self.fields['pubmed_ids'] = forms.CharField(
            label='PubMed identifiers',
            help_text='Search by PubMed identifiers associated with an entry.',
            required=False,
            widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.identifier, i.identifier)
                    for i in PubmedIdentifier.objects.all()
                ]))
            ),
        )
        self.fields['sra_ids'] = forms.CharField(
            label='SRA accessions',
            help_text='Search by SRA accessions associated with an entry.',
            required=False,
            widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.identifier, i.identifier)
                    for i in SraIdentifier.objects.all()
                ]))
            ),
        )
        self.fields['doi_ids'] = forms.CharField(
            label='DOI accessions',
            help_text='Search by DOI accessions associated with an entry.',
            required=False,
            widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.identifier, i.identifier)
                    for i in DoiIdentifier.objects.all()
                ]))
            ),
        )

    def clean_pubmed_ids(self):
        field_name = 'pubmed_ids'
        instances = parse_char_list(self.cleaned_data.get(field_name, []))
        instances = list(set([i for i in instances if not is_null(i)]))
        return instances

    def clean_sra_ids(self):
        field_name = 'sra_ids'
        instances = parse_char_list(self.cleaned_data.get(field_name, []))
        instances = list(set([i for i in instances if not is_null(i)]))
        return instances

    def clean_doi_ids(self):
        field_name = 'doi_ids'
        instances = parse_char_list(self.cleaned_data.get(field_name, []))
        instances = list(set([i for i in instances if not is_null(i)]))
        return instances

    def make_filters(self, join=True, filter_=experiment_filter):
        data = self.cleaned_data
        search_dict = {
            'pubmed': data.get('pubmed_ids', []),
            'sra': data.get('sra_ids', []),
            'doi': data.get('doi_ids', []),
        }
        join_func = None
        if join:
            join_func = filter_.and_join_qs
        return filter_.search_all(search_dict, join_func=join_func)


class TargetIdentifierSearchForm(forms.Form, FormFilterMixin):
    """
    Search by uniprot, refseq, ensembl and genome assembly.
    """
    def __init__(self, *args, **kwargs):
        super(TargetIdentifierSearchForm, self).__init__(*args, **kwargs)
        self.fields['uniprot'] = forms.CharField(
            label='UniProt accession',
            help_text='Search by a target\'s UniProt accession.',
            required=False,
            widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.identifier, i.identifier)
                    for i in UniprotIdentifier.objects.all()
                ]))
            ),
        )
        self.fields['refseq'] = forms.CharField(
            label='RefSeq accession',
            help_text='Search by a target\'s RefSeq accession.',
            required=False,
            widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.identifier, i.identifier)
                    for i in RefseqIdentifier.objects.all()
                ]))
            ),
        )
        self.fields['ensembl'] = forms.CharField(
            required=False,
            label='Ensembl accession',
            help_text='Search by a target\'s Ensembl accession.',
            widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.identifier, i.identifier)
                    for i in EnsemblIdentifier.objects.all()
                ]))
            ),
        )
        self.fields['target'] = forms.CharField(
            required=False,
            label='Target gene name',
            help_text='Search by a target\'s gene name.',
            widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.name, i.name)
                    for i in TargetGene.objects.all()
                ]))
            ),
        )

    def clean_uniprot(self):
        field_name = 'uniprot'
        instances = parse_char_list(self.cleaned_data.get(field_name, []))
        instances = list(set([i for i in instances if not is_null(i)]))
        return instances

    def clean_refseq(self):
        field_name = 'refseq'
        instances = parse_char_list(self.cleaned_data.get(field_name, []))
        instances = list(set([i for i in instances if not is_null(i)]))
        return instances

    def clean_ensembl(self):
        field_name = 'ensembl'
        instances = parse_char_list(self.cleaned_data.get(field_name, []))
        instances = list(set([i for i in instances if not is_null(i)]))
        return instances

    def clean_target(self):
        field_name = 'target'
        instances = parse_char_list(self.cleaned_data.get(field_name, []))
        instances = list(set([i for i in instances if not is_null(i)]))
        return instances

    def make_filters(self, join=True, filter_=experiment_filter):
        data = self.cleaned_data
        search_dict = {
            'uniprot': data.get('uniprot', []),
            'refseq': data.get('refseq', []),
            'ensembl': data.get('ensembl', []),
            'target': data.get('target', []),
        }
        join_func = None
        if join:
            join_func = filter_.and_join_qs
        return filter_.search_all(search_dict, join_func=join_func)


class GenomeSearchForm(forms.Form, FormFilterMixin):
    """Search by genome name and assembly"""
    def __init__(self, *args, **kwargs):
        super(GenomeSearchForm, self).__init__(*args, **kwargs)
        self.fields['genome'] = forms.CharField(
            required=False,
            label='Reference name',
            help_text='Search by a target\'s reference genome.',
            widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.short_name, i.short_name)
                    for i in ReferenceGenome.objects.all()
                ]))
            ),
        )
        self.fields['assembly'] = forms.CharField(
            required=False,
            label='Assembly accession',
            help_text='Search by a target\'s reference assembly accession.',
            widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.identifier, i.identifier)
                    for i in GenomeIdentifier.objects.all()
                ]))
            ),
        )
        self.fields['species'] = forms.CharField(
            required=False,
            label='Reference species',
            help_text='Search by a target\'s reference genome species.',
            widget=forms.SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.species_name, i.species_name)
                    for i in ReferenceGenome.objects.all()
                ]))
            )
        )

    def clean_genome(self):
        field_name = 'genome'
        instances = parse_char_list(self.cleaned_data.get(field_name, []))
        instances = list(set([i for i in instances if not is_null(i)]))
        return instances

    def clean_species(self):
        field_name = 'species'
        instances = parse_char_list(self.cleaned_data.get(field_name, []))
        instances = list(set([i for i in instances if not is_null(i)]))
        return instances

    def clean_assembly(self):
        field_name = 'assembly'
        instances = parse_char_list(self.cleaned_data.get(field_name, []))
        instances = list(set([i for i in instances if not is_null(i)]))
        return instances

    def make_filters(self, join=True, filter_=experiment_filter):
        data = self.cleaned_data
        search_dict = {
            'species': data.get('species', []),
            'genome': data.get('genome', []),
            'assembly': data.get('assembly', []),
        }
        join_func = None
        if join:
            join_func = filter_.and_join_qs
        return filter_.search_all(search_dict, join_func=join_func)
