
import django.forms as forms

from main.utils.query_parsing import parse_query, filter_empty
from experiment.models import Experiment, ScoreSet


class SearchForm(forms.Form):
    accessions = forms.CharField(
        max_length=None, label="Accessions", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control", "placeholder": "Comma delimited"}
        )
    )
    ext_accessions = forms.CharField(
        max_length=None, label="External Accessions", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control", "placeholder": "Comma delimited"}
        )
    )
    keywords = forms.CharField(
        max_length=None, label="Keywords", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control", "placeholder": "Comma delimited"}
        )
    )
    targets = forms.CharField(
        max_length=None, label="Target", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control", "placeholder": "Comma delimited"}
        )
    )
    target_organisms = forms.CharField(
        max_length=None, label="Target Organism", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control", "placeholder": "Comma delimited"}
        )
    )
    authors = forms.CharField(
        max_length=None, label="Contributors", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control", "placeholder": "Comma delimited"}
        )
    )
    metadata = forms.CharField(
        max_length=None, label="Metadata", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control", "placeholder": "Comma delimited"}
        )
    )

    def clean_accessions(self):
        return filter_empty(
            parse_query(self.cleaned_data.get("accessions", ""))
        )

    def clean_ext_accessions(self):
        return filter_empty(
            parse_query(self.cleaned_data.get("ext_accessions", ""))
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

    def clean_authors(self):
        return filter_empty(
            parse_query(self.cleaned_data.get("authors", ""))
        )

    def clean_metadata(self):
        return filter_empty(
            parse_query(self.cleaned_data.get("metadata", ""))
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

    def search_by_accession(self, model, accessions):
        if accessions:
            entries = model.objects.none()
            for accession in accessions:
                entries |= model.objects.all().filter(
                    accession__iexact=accession
                )
            return entries
        return None

    def search_by_target(self, model, targets):
        if targets:
            entries = model.objects.none()
            for target in targets:
                entries |= model.objects.all().filter(
                    target__iexact=target
                )
            return entries
        return None

    def search_by_metadata(self, model, metadata_tags):
        if metadata_tags:
            entries = model.objects.none()
            for tag in metadata_tags:
                entries |= model.objects.all().filter(
                    abstract__icontains=tag)
                entries |= model.objects.all().filter(
                    method_desc__icontains=tag
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

    def search_by_authors(self, model, authors):
        if authors:
            selected = set()
            entries = model.objects.none()
            model_author_ls = [
                (m.pk, m.get_authors_by_full_name())
                for m in model.objects.all()
            ]

            for author in authors:
                for pk, model_authors in model_author_ls:
                    if model_authors.lower().find(author.lower()) > -1:
                        selected.add(pk)

            entries |= model.objects.all().filter(pk__in=selected)
            return entries
        return None

    def search_by_external_accession(self, ext_accessions):
        if ext_accessions:
            entries = []
            queried_exas = set([exa.lower() for exa in ext_accessions])
            for instance in Experiment.objects.all():
                instance_exas = set([
                    exa.text.lower()
                    for exa in instance.external_accessions.all()
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
                "authors", None
            ) or search_all
            accessions = self.cleaned_data.get(
                "accessions", None
            ) or search_all
            metadata_tags = self.cleaned_data.get(
                "metadata", None
            ) or search_all
            targets = self.cleaned_data.get(
                "targets", None
            ) or search_all
            ext_accessions = self.cleaned_data.get(
                "ext_accessions", None
            ) or search_all
            target_organisms = self.cleaned_data.get(
                "target_organisms", None
            ) or search_all

            keyword_hits = self.search_by_keyword(model, keywords)
            accessions_hits = self.search_by_accession(model, accessions)
            metadata_hits = self.search_by_metadata(model, metadata_tags)
            author_hits = self.search_by_authors(model, authors)

            if model == Experiment:
                targets_hits = self.search_by_target(model, targets)
                ext_accessions_hits = self.search_by_external_accession(
                    ext_accessions
                )
                target_organism_hits = self.search_by_target_organism(
                    target_organisms
                )
            else:
                ext_accessions_hits = None
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

            if accessions_hits is not None:
                if not union_search:
                    instances &= accessions_hits
                else:
                    instances |= accessions_hits

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

            if ext_accessions_hits is not None:
                if not union_search:
                    instances &= ext_accessions_hits
                else:
                    instances |= ext_accessions_hits

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
