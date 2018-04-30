import django.forms as forms


from core.utilities.query_parsing import parse_query


class SearchForm(forms.Form):
    urns = forms.CharField(
        max_length=None, label="URN", required=False,
        widget=forms.widgets.TextInput()
    )
    external_identifiers = forms.CharField(
        max_length=None, label="External identifiers", required=False,
        help_text=(
            'Search using PubMed, UniProt, RefSeq, GenBank, '
            'Ensembl, SRA and DOI accessions.'
        ),
        widget=forms.widgets.TextInput()
    )
    keywords = forms.CharField(
        max_length=None, label="Keywords", required=False,
        help_text='Search entries by keyword.',
        widget=forms.widgets.TextInput()
    )
    targets = forms.CharField(
        max_length=None, label="Target", required=False,
        help_text='Search using a target gene name.',
        widget=forms.widgets.TextInput()
    )
    target_organisms = forms.CharField(
        max_length=None, label="Target organism", required=False,
        help_text='Search by the organism of a target gene.',
        widget=forms.widgets.TextInput()
    )
    metadata = forms.CharField(
        max_length=None, label="Full text", required=False,
        help_text=(
            'Search entries by their title, description, method and abstract.'
        ),
        widget=forms.widgets.TextInput()
    )

    def clean_urns(self):
        return parse_query(self.cleaned_data.get("urns", ""))

    def clean_external_identifiers(self):
        return parse_query(self.cleaned_data.get("external_identifiers", ""))

    def clean_targets(self):
        return parse_query(self.cleaned_data.get("targets", ""))

    def clean_target_organisms(self):
        return parse_query(self.cleaned_data.get("target_organisms", ""))

    def clean_metadata(self):
        return parse_query(self.cleaned_data.get("metadata", ""))

    def clean_keywords(self):
        return parse_query(self.cleaned_data.get("keywords", ""))

    def base_search_dict(self):
        data = self.cleaned_data
        dict_ = {
            'urn': data.get('urns', []),
            'abstract': data.get('metadata', ""),
            'method': data.get('metadata', ""),
            'title': data.get('metadata', ""),
            'description': data.get('metadata', ""),
            'keywords': data.get('keywords', []),
            'sra':  data.get('external_identifiers', []),
            'doi':  data.get('external_identifiers', []),
            'pubmed':  data.get('external_identifiers', []),
        }
        return dict_

    def experiment_search_dict(self):
        data = self.cleaned_data
        base = self.base_search_dict()
        base.update({
            'target': data.get('targets', []),
            'organism': data.get('target_organisms', []),
            'uniprot': data.get('external_identifiers', []),
            'ensembl': data.get('external_identifiers', []),
            'refseq': data.get('external_identifiers', []),
            'genome': data.get('external_identifiers', []),
        })
        return base
