import django.forms as forms

from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet

from core.utilities.query_parsing import parse_query, filter_empty


class SearchForm(forms.Form):
    urns = forms.CharField(
        max_length=None, label="Urns", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control"}
        )
    )
    doi_ids = forms.CharField(
        max_length=None, label="DOI", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control"}
        )
    )
    sra_ids = forms.CharField(
        max_length=None, label="SRA", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control"}
        )
    )
    pmid_ids = forms.CharField(
        max_length=None, label="PubMed", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control"}
        )
    )
    keywords = forms.CharField(
        max_length=None, label="Keywords", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control"}
        )
    )
    # targets = forms.CharField(
    #     max_length=None, label="Target", required=False,
    #     widget=forms.widgets.TextInput(
    #         attrs={"class": "form-control"}
    #     )
    # )
    # target_organisms = forms.CharField(
    #     max_length=None, label="Target Organism", required=False,
    #     widget=forms.widgets.TextInput(
    #         attrs={"class": "form-control"}
    #     )
    # )
    contributors = forms.CharField(
        max_length=None, label="Contributors", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control"}
        )
    )

    def clean_urns(self):
        return filter_empty(
            parse_query(self.cleaned_data.get("urns", ""))
        )

    def clean_doi_ids(self):
        return filter_empty(
            parse_query(self.cleaned_data.get("doi_ids", ""))
        )

    def clean_sra_ids(self):
        return filter_empty(
            parse_query(self.cleaned_data.get("sra_ids", ""))
        )

    def clean_pmid_ids(self):
        return filter_empty(
            parse_query(self.cleaned_data.get("pubmed_ids", ""))
        )

    def clean_keywords(self):
        return filter_empty(
            parse_query(self.cleaned_data.get("keywords", ""))
        )

    def clean_targets(self):
        return filter_empty(
            parse_query(self.cleaned_data.get("targets", ""))
        )

    def clean_target_organisms(self):
        return filter_empty(
            parse_query(self.cleaned_data.get("target_organisms", ""))
        )

    def clean_contributors(self):
        return filter_empty(
            parse_query(self.cleaned_data.get("contributors", ""))
        )

    def clean(self):
        cleaned_data = super(SearchForm, self).clean()
        if 'search_all' in self.data:
            cleaned_data['search_all'] = filter_empty(parse_query(
                self.data.get("search_all")
            ))
        return cleaned_data

    def search_by_keyword(self, model, keywords):
        if keywords:
            entries = []
            queried_kws = set([kw.lower() for kw in keywords])
            for instance in model.objects.all():
                instance_kws = set(
                    [kw.text.lower() for kw in instance.keywords.all()]
                )
                if queried_kws & instance_kws:
                    entries.append(instance.pk)

            return model.objects.filter(pk__in=entries)
        return None

    def search_by_urn(self, model, urns):
        if urns:
            entries = model.objects.none()
            for urn in urns:
                entries |= model.objects.all().filter(
                    urn__iexact=urn
                )
            return entries
        return None

    def search_by_target(self, model, targets):
        if targets:
            entries = model.objects.none()
            for target in targets:
                entries |= model.objects.all().filter(
                    target__icontains=target
                )
            return entries
        return None

    def search_by_metadata(self, model, metadata_tags):
        if metadata_tags:
            entries = model.objects.none()
            for tag in metadata_tags:
                entries |= model.objects.all().filter(
                    abstract_text__icontains=tag)
                entries |= model.objects.all().filter(
                    method_text__icontains=tag
                )
            return entries
        return None

    def search_by_target_organism(self, target_organisms):
        if target_organisms:
            entries = []
            queried_tos = set([to.lower() for to in target_organisms])
            for instance in Experiment.objects.all():
                instance_tos = set([
                    to.text.lower()
                    for to in instance.target_organism.all()
                ])
                if queried_tos & instance_tos:
                    entries.append(instance.pk)

            entries = Experiment.objects.filter(pk__in=entries)
            return entries
        return None

    def search_by_contributors(self, model, contributors):
        if contributors:
            selected = set()
            entries = model.objects.none()
            model_contributors_ls = [
                (m.pk, m.format_using_full_name('editors', string=True))
                for m in model.objects.all()
            ]
            model_contributors_ls += [
                (m.pk, m.format_using_username('editors', string=True))
                for m in model.objects.all()
            ]

            for c in contributors:
                for pk, model_contributors in model_contributors_ls:
                    if model_contributors.lower().find(c.lower()) > -1:
                        selected.add(pk)

            entries |= model.objects.all().filter(pk__in=selected)
            return entries
        return None

    def search_by_external_identifier(self, ext_ids, field_name):
        if ext_ids:
            entries = []
            queried_exas = set([exa.lower() for exa in ext_ids])
            for instance in Experiment.objects.all():
                instance_exas = set([
                    exa.identifier.lower()
                    for exa in getattr(instance, field_name).all()
                ])
                if queried_exas & instance_exas:
                    entries.append(instance.pk)

            entries = Experiment.objects.filter(pk__in=entries)
            return entries
        return None

    def query_model(self, model, union_search=False):
        if self.is_bound and self.is_valid():
            search_all = self.cleaned_data.get("search_all", [])
            keywords = self.cleaned_data.get(
                "keywords", None
            ) or search_all
            authors = self.cleaned_data.get(
                "contributors", None
            ) or search_all
            urns = self.cleaned_data.get(
                "urns", None
            ) or search_all
            metadata_tags = self.cleaned_data.get(
                "metadata", None
            ) or search_all
            targets = self.cleaned_data.get(
                "targets", None
            ) or search_all
            doi_ids = self.cleaned_data.get(
                "doi_ids", None
            ) or search_all
            sra_ids = self.cleaned_data.get(
                "sra_ids", None
            ) or search_all
            pmid_ids = self.cleaned_data.get(
                "pubmed_ids", None
            ) or search_all
            target_organisms = self.cleaned_data.get(
                "target_organisms", None
            ) or search_all

            keyword_hits = self.search_by_keyword(model, keywords)
            urns_hits = self.search_by_urn(model, urns)
            metadata_hits = self.search_by_metadata(model, metadata_tags)
            author_hits = self.search_by_contributors(model, authors)

            if model == Experiment:
                targets_hits = self.search_by_target(model, targets)
                doi_ids_hits = self.search_by_external_identifier(doi_ids, 'doi_ids')
                sra_ids_hits = self.search_by_external_identifier(sra_ids, 'sra_ids')
                pmid_ids_hits = self.search_by_external_identifier(pmid_ids, 'pubmed_ids')
                target_organism_hits = self.search_by_target_organism(
                    target_organisms
                )
            else:
                doi_ids_hits = None
                sra_ids_hits = None
                pmid_ids_hits = None
                target_organism_hits = None
                targets_hits = None

            if union_search:
                instances = model.objects.none()
            else:
                instances = model.objects.all()

            if keyword_hits is not None:
                if not union_search:
                    instances &= keyword_hits
                else:
                    instances |= keyword_hits

            if author_hits is not None:
                if not union_search:
                    instances &= author_hits
                else:
                    instances |= author_hits

            if urns_hits is not None:
                if not union_search:
                    instances &= urns_hits
                else:
                    instances |= urns_hits

            if targets_hits is not None:
                if not union_search:
                    instances &= targets_hits
                else:
                    instances |= targets_hits

            if metadata_hits is not None:
                if not union_search:
                    instances &= metadata_hits
                else:
                    instances |= metadata_hits

            if doi_ids_hits is not None:
                if not union_search:
                    instances &= doi_ids_hits
                else:
                    instances |= doi_ids_hits

            if sra_ids_hits is not None:
                if not union_search:
                    instances &= sra_ids_hits
                else:
                    instances |= sra_ids_hits

            if pmid_ids_hits is not None:
                if not union_search:
                    instances &= pmid_ids_hits
                else:
                    instances |= pmid_ids_hits

            if target_organism_hits is not None:
                if not union_search:
                    instances &= target_organism_hits
                else:
                    instances |= target_organism_hits

            return instances

    def query_experiments(self):
        search_all = self.cleaned_data.get("search_all", [])
        union_search = True if search_all else False
        return self.query_model(Experiment, union_search)

    def query_scoresets(self):
        search_all = self.cleaned_data.get("search_all", [])
        union_search = True if search_all else False
        return self.query_model(ScoreSet, union_search)
