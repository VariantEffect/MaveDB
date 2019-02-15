import django.forms as forms
from django.contrib.auth import get_user_model

from core import fields

from genome.models import ReferenceGenome, TargetGene
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

from dataset import filters as ds_filters
from accounts.mixins import filter_anon
from accounts import filters as user_filters


User = get_user_model()


class BasicSearchForm(forms.Form):
    search = forms.CharField(required=False)

    def format_data_for_filter(self):
        if not self.is_valid():
            return {}
        
        value = self.cleaned_data.get('search', "")
        if not value:
            return {}

        data = dict()

        # DatasetModel Filter fields
        # -------------------------------------------------------------- #
        data[ds_filters.DatasetModelFilter.URN] = value
        data[ds_filters.DatasetModelFilter.TITLE] = value
        data[ds_filters.DatasetModelFilter.DESCRIPTION] = value
        data[ds_filters.DatasetModelFilter.METHOD] = value
        data[ds_filters.DatasetModelFilter.ABSTRACT] = value
        data[ds_filters.DatasetModelFilter.PUBMED] = value
        data[ds_filters.DatasetModelFilter.SRA] = value
        data[ds_filters.DatasetModelFilter.DOI] = value
        data[ds_filters.DatasetModelFilter.KEYWORD] = value

        # User filter fields
        # -------------------------------------------------------------- #
        data[ds_filters.DatasetModelFilter.FIRST_NAME] = value
        data[ds_filters.DatasetModelFilter.LAST_NAME] = value
        data[ds_filters.DatasetModelFilter.USERNAME] = value
        data[ds_filters.DatasetModelFilter.DISPLAY_NAME] = value

        # ScoreSet/Experiment filter fields
        # -------------------------------------------------------------- #
        data[ds_filters.ScoreSetFilter.TARGET] = value
        data[ds_filters.ScoreSetFilter.ORGANISM] = value
        data[ds_filters.ScoreSetFilter.GENOME] = value
        data[ds_filters.ScoreSetFilter.UNIPROT] = value
        data[ds_filters.ScoreSetFilter.ENSEMBL] = value
        data[ds_filters.ScoreSetFilter.REFSEQ] = value
        data[ds_filters.ScoreSetFilter.LICENCE] = value
        data[ds_filters.ScoreSetFilter.TARGET_TYPE] = value

        return data


class AdvancedSearchForm(forms.Form):
    # DatasetModel Filter fields
    # ---------------------------------------------------------------------- #
    title = forms.CharField(
        label="Title", required=False,
        help_text='Search entries by title.',
    )
    # description = forms.CharField(
    #     label="Description", required=False,
    #     help_text='Search entries by short description.',
    #     widget=forms.widgets.Textarea()
    # )
    # method = forms.CharField(
    #     label="Method", required=False,
    #     help_text='Search entries by their method description.',
    #     widget=forms.widgets.Textarea()
    # )
    # abstract = forms.CharField(
    #     label="Abstract", required=False,
    #     help_text='Search entries by their abstract description.',
    #     widget=forms.widgets.Textarea()
    # )
    
    pubmed = fields.CSVCharField(
        label='PubMed identifiers', required=False,
        help_text='Search by PubMed identifiers associated with an entry.',
    )
    sra = fields.CSVCharField(
        label='SRA accessions', required=False,
        help_text='Search by SRA accessions associated with an entry.',
    )
    doi = fields.CSVCharField(
        label='DOI accessions', required=False,
        help_text='Search by DOI accessions associated with an entry.',
    )
    keyword = fields.CSVCharField(
        label='Keywords', required=False,
        help_text='Search for entries associated with a keyword.',
    )

    # User filter fields
    # ---------------------------------------------------------------------- #
    first_name = fields.CSVCharField(
        max_length=None, label='Contributor first name', required=False,
        help_text='Search by a contributor\'s first name'
    )
    last_name = fields.CSVCharField(
        max_length=None, label='Contributor last name', required=False,
        help_text='Search by a contributor\'s last name'
    )
    username = fields.CSVCharField(
        max_length=None, label='Contributor ORCID', required=False,
        help_text='Search by a contributor\'s ORCID'
    )
    display_name = fields.CSVCharField(
        max_length=None, label='Contributor display name', required=False,
        help_text='Search by a contributor\'s display name'
    )
    
    # ScoreSet/Experiment filter fields
    # ---------------------------------------------------------------------- #
    target = fields.CSVCharField(
        label='Target name', required=False,
        help_text='Search by a target\'s name.',
    )
    target_type = fields.CSVCharField(
        label='Target type', required=False,
        help_text='Search by a target\'s type.',
    )
    organism = fields.CSVCharField(
        label='Reference organism', required=False,
        help_text='Search by a target\'s reference genome organism.',
    )
    genome = fields.CSVCharField(
        label='Reference name/assembly identifier', required=False,
        help_text='Search by a target\'s reference genome by name or assembly '
                  'identifier',
    )
    uniprot = fields.CSVCharField(
        label='UniProt accession',
        help_text='Search by a target\'s UniProt accession.',
        required=False,
    )
    ensembl = fields.CSVCharField(
        required=False, label='Ensembl accession',
        help_text='Search by a target\'s Ensembl accession.',
    )
    refseq = fields.CSVCharField(
        label='RefSeq accession', required=False,
        help_text='Search by a target\'s RefSeq accession.',
    )
    licence = fields.CSVCharField(
        label='Licence', required=False,
        help_text="Search for Score Sets with the selected licence type.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # These must be loaded when the form is served so the the queryset
        # is dynamically loaded to show new entries.
        
        # DatasetModel Filter fields
        # ------------------------------------------------------------------- #
        self.fields['sra'].widget = forms.SelectMultiple(
            attrs={"class": "select2 select2-token-select"},
            choices=sorted(set([
                (i.identifier, i.identifier)
                for i in SraIdentifier.objects.all()
            ]))
        )
        self.fields['doi'].widget = forms.SelectMultiple(
            attrs={"class": "select2 select2-token-select"},
            choices=sorted(set([
                (i.identifier, i.identifier)
                for i in PubmedIdentifier.objects.all()
            ]))
        )
        self.fields['pubmed'].widget = forms.SelectMultiple(
            attrs={"class": "select2 select2-token-select"},
            choices=sorted(set([
                (i.identifier, i.identifier)
                for i in DoiIdentifier.objects.all()
            ]))
        )
        self.fields['keyword'].widget = forms.SelectMultiple(
            attrs={"class": "select2 select2-token-select"},
            choices=sorted(set([
                (i.text, i.text)
                for i in Keyword.objects.all()
            ]))
        )

        # User filter fields
        # ------------------------------------------------------------------- #
        self.fields[user_filters.UserFilter.USERNAME].widget = forms.\
            SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.username, i.username)
                    for i in filter_anon(User.objects.filter(
                        is_superuser=False))
                ]))
            )
        self.fields[user_filters.UserFilter.FIRST_NAME].widget = forms.\
            SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.first_name, i.first_name)
                    for i in filter_anon(User.objects.filter(
                        is_superuser=False))
                ]))
            )
        self.fields[user_filters.UserFilter.LAST_NAME].widget = forms.\
            SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.last_name, i.last_name)
                    for i in filter_anon(User.objects.filter(
                        is_superuser=False))
                ]))
            )
        self.fields[user_filters.UserFilter.DISPLAY_NAME].widget = forms.\
            SelectMultiple(
                attrs={"class": "select2 select2-token-select"},
                choices=sorted(set([
                    (i.profile.get_display_name(), i.profile.get_display_name())
                    for i in filter_anon(User.objects.filter(
                        is_superuser=False))
                ]))
            )

        # ScoreSet/Experiment filter fields
        # ------------------------------------------------------------------- #
        self.fields['licence'].widget = forms.SelectMultiple(
            attrs={"class": "select2 select2-token-select"},
            choices=sorted(set([
                (i.long_name, i.long_name)
                for i in Licence.objects.all()
            ]))
        )
        self.fields['target'].widget = forms.SelectMultiple(
            attrs={"class": "select2 select2-token-select"},
            choices=sorted(set([
                (i.name, i.name)
                for i in TargetGene.objects.all()
            ]))
        )
        self.fields['target_type'].widget = forms.SelectMultiple(
            attrs={"class": "select2 select2-token-select"},
            choices=TargetGene.CATEGORY_CHOICES
        )
        self.fields['genome'].widget = forms.SelectMultiple(
            attrs={"class": "select2 select2-token-select"},
            choices=sorted(set([
                (i.short_name, i.short_name)
                for i in ReferenceGenome.objects.all()
            ])) + sorted(set([
                (i.identifier, i.identifier)
                for i in GenomeIdentifier.objects.all()
            ]))
        )
        self.fields['organism'].widget = forms.SelectMultiple(
            attrs={"class": "select2 select2-token-select"},
            choices=sorted(set([
                (i.organism_name, i.organism_name)
                for i in ReferenceGenome.objects.all()
            ]))
        )
        self.fields['uniprot'].widget = forms.SelectMultiple(
            attrs={"class": "select2 select2-token-select"},
            choices=sorted(set([
                (i.identifier, i.identifier)
                for i in UniprotIdentifier.objects.all()
            ]))
        )
        self.fields['refseq'].widget = forms.SelectMultiple(
            attrs={"class": "select2 select2-token-select"},
            choices=sorted(set([
                (i.identifier, i.identifier)
                for i in RefseqIdentifier.objects.all()
            ]))
        )
        self.fields['ensembl'].widget = forms.SelectMultiple(
            attrs={"class": "select2 select2-token-select"},
            choices=sorted(set([
                (i.identifier, i.identifier)
                for i in EnsemblIdentifier.objects.all()
            ]))
        )
        
    def format_data_for_filter(self):
        if not self.is_valid():
            return {}

        data = {}
        # DatasetModel Filter fields
        # ------------------------------------------------------------------- #
        title = self.cleaned_data.get('title', "").strip()
        # description = self.cleaned_data.get('description', "").strip()
        # method = self.cleaned_data.get('method', "").strip()
        # abstract = self.cleaned_data.get('abstract', "").strip()
        pubmed = ','.join(self.cleaned_data.get('pubmed', []))
        sra = ','.join(self.cleaned_data.get('sra', []))
        doi = ','.join(self.cleaned_data.get('doi', []))
        keyword = ','.join(self.cleaned_data.get('keyword', []))
        
        if title:
            data[ds_filters.DatasetModelFilter.TITLE] = title
        # if description:
        #     data[ds_filters.DatasetModelFilter.DESCRIPTION] = description
        # if method:
        #     data[ds_filters.DatasetModelFilter.METHOD] = method
        # if abstract:
        #     data[ds_filters.DatasetModelFilter.ABSTRACT] = abstract
        if pubmed:
            data[ds_filters.DatasetModelFilter.PUBMED] = pubmed
        if sra:
            data[ds_filters.DatasetModelFilter.SRA] = sra
        if doi:
            data[ds_filters.DatasetModelFilter.DOI] = doi
        if keyword:
            data[ds_filters.DatasetModelFilter.KEYWORD] = keyword
        
        # User filter fields
        # ------------------------------------------------------------------- #
        first_name = ','.join(self.cleaned_data.get('first_name', []))
        last_name = ','.join(self.cleaned_data.get('last_name', []))
        username = ','.join(self.cleaned_data.get('username', []))
        display_name = ','.join(self.cleaned_data.get('display_name', []))
        
        if first_name:
            data[ds_filters.DatasetModelFilter.FIRST_NAME] = first_name
        if last_name:
            data[ds_filters.DatasetModelFilter.LAST_NAME] = last_name
        if username:
            data[ds_filters.DatasetModelFilter.USERNAME] = username
        if display_name:
            data[ds_filters.DatasetModelFilter.DISPLAY_NAME] = display_name

        # ScoreSet/Experiment filter fields
        # ------------------------------------------------------------------- #
        target = ','.join(self.cleaned_data.get('target', []))
        target_type = ','.join(self.cleaned_data.get('target_type', []))
        organism = ','.join(self.cleaned_data.get('organism', []))
        genome = ','.join(self.cleaned_data.get('genome', []))
        uniprot = ','.join(self.cleaned_data.get('uniprot', []))
        ensembl = ','.join(self.cleaned_data.get('ensembl', []))
        refseq = ','.join(self.cleaned_data.get('refseq', []))
        licence = ','.join(self.cleaned_data.get('licence', []))
        
        if target:
            data[ds_filters.ScoreSetFilter.TARGET] = target
        if target_type:
            data[ds_filters.ScoreSetFilter.TARGET_TYPE] = target_type
        if organism:
            data[ds_filters.ScoreSetFilter.ORGANISM] = organism
        if genome:
            data[ds_filters.ScoreSetFilter.GENOME] = genome
        if uniprot:
            data[ds_filters.ScoreSetFilter.UNIPROT] = uniprot
        if ensembl:
            data[ds_filters.ScoreSetFilter.ENSEMBL] = ensembl
        if refseq:
            data[ds_filters.ScoreSetFilter.REFSEQ] = refseq
        if licence:
            data[ds_filters.ScoreSetFilter.LICENCE] = licence

        return data
