
import django.forms as forms

from main.utils.query_parsing import parse_query
from experiment.models import Experiment
from scoreset.models import ScoreSet


class SearchForm(forms.Form):
    accession = forms.CharField(
        max_length=None, label="Accession", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control"}
        )
    )
    ext_accessions = forms.CharField(
        max_length=None, label="External Accessions", required=False,
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
    target = forms.CharField(
        max_length=None, label="Target", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control"}
        )
    )
    target_organism = forms.CharField(
        max_length=None, label="Target Organism", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control"}
        )
    )
    authors = forms.CharField(
        max_length=None, label="Authors", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control"}
        )
    )
    metadata = forms.CharField(
        max_length=None, label="Metadata", required=False,
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control"}
        )
    )

    def clean_accession(self):
        return parse_query(self.cleaned_data.get("accession", ""))

    def clean_ext_accessions(self):
        return parse_query(self.cleaned_data.get("ext_accessions", ""))

    def clean_keywords(self):
        return parse_query(self.cleaned_data.get("keywords", ""))

    def clean_target(self):
        return parse_query(self.cleaned_data.get("target", ""))

    def clean_target_organism(self):
        return parse_query(self.cleaned_data.get("target_organism", ""))

    def clean_authors(self):
        return parse_query(self.cleaned_data.get("authors", ""))

    def clean_metadata(self):
        return parse_query(self.cleaned_data.get("metadata", ""))

    def clean(self):
        cleaned_data = super(SearchForm, self).clean()
        if 'search_all' in self.data:
            cleaned_data['search_all'] = parse_query(
                self.data.get("search_all")
            )
        return cleaned_data

    def search_model(self, model):
        instances = model.objects.all()

        # Experiment specific model attributes
        # ----------------------------------------------------------------- #
        if model == Experiment:
            target_organism = self.cleaned_data.get("target_organism", None)
            if target_organism:
                entries = []
                queried_tos = set([to.lower() for to in target_organism])
                for instance in instances:
                    instance_tos = set([
                        to.text.lower()
                        for to in instance.target_organism.all()
                    ])
                    if queried_tos & instance_tos:
                        entries.append(instance.pk)

                entries = model.objects.filter(pk__in=entries)
                instances &= entries

            ext_accessions = self.cleaned_data.get("ext_accessions", None)
            if ext_accessions:
                entries = []
                queried_exas = set([exa.lower() for exa in ext_accessions])
                for instance in instances:
                    instance_exas = set([
                        exa.text.lower()
                        for exa in instance.external_accessions.all()
                    ])
                    if queried_exas & instance_exas:
                        entries.append(instance.pk)

                entries = model.objects.filter(pk__in=entries)
                instances &= entries

        # Base model attributes
        # ----------------------------------------------------------------- #
        accessions = self.cleaned_data.get("accession", None)
        if accessions:
            entries = model.objects.none()
            for accession in accessions:
                entries |= model.objects.all().filter(
                    accession__iexact=accession
                )
            instances &= entries

        keywords = self.cleaned_data.get("keywords", None)
        if keywords:
            entries = []
            queried_kws = set([kw.lower() for kw in keywords])
            for instance in instances:
                instance_kws = set(
                    [kw.text.lower() for kw in instance.keywords.all()]
                )
                if queried_kws & instance_kws:
                    entries.append(instance.pk)

            entries = model.objects.filter(pk__in=entries)
            instances &= entries

        metadata = self.cleaned_data.get("metadata", None)
        if metadata:
            entries = model.objects.none()
            for tag in metadata:
                entries |= model.objects.all().filter(
                    abstract__icontains=tag)
                entries |= model.objects.all().filter(
                    method_desc__icontains=tag
                )
            instances &= entries

        targets = self.cleaned_data.get("target", None)
        if targets:
            entries = model.objects.none()
            for target in targets:
                entries |= model.objects.all().filter(
                    target__iexact=target
                )
            instances &= entries

        return instances

    def query_experiments(self):
        return self.search_model(Experiment)

    def query_scoresets(self):
        return self.search_model(ScoreSet)
