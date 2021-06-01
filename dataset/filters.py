import re
import csv

from django_filters import FilterSet, filters, constants
from django.db.models import Q
from django.contrib.auth.models import Group, User

from django import forms

from core.filters import CSVCharFilter

from . import models


digit_re = re.compile(r"\d+")


class DatasetModelFilter(FilterSet):
    """
    Filter for the base `DatasetModel` fields:
        - urn
        - title
        - short_description
        - abstract
        - method
        - doi_ids
        - sra_ids
        - pubmed_ids
        - keywords
        - contributor first name
        - contributor last name
        - contributor username
        - contributor display name
    """

    URN = "urn"
    TITLE = "title"
    DESCRIPTION = "description"
    ABSTRACT = "abstract"
    METHOD = "method"
    DOI = "doi"
    SRA = "sra"
    PUBMED = "pubmed"
    KEYWORD = "keyword"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    USERNAME = "username"
    DISPLAY_NAME = "display_name"

    class Meta:
        fields = (
            "title",
            "description",
            "abstract",
            "method",
            "doi",
            "sra",
            "pubmed",
            "first_name",
            "last_name",
            "username",
            "display_name",
        )

    urn = CSVCharFilter(field_name="urn", lookup_expr="icontains")
    title = filters.CharFilter(field_name="title", lookup_expr="icontains")
    description = filters.CharFilter(
        field_name="short_description", lookup_expr="icontains"
    )
    abstract = filters.CharFilter(
        field_name="abstract_text", lookup_expr="icontains"
    )
    method = filters.CharFilter(
        field_name="method_text", lookup_expr="icontains"
    )
    doi = CSVCharFilter(
        field_name="doi_ids__identifier", lookup_expr="icontains"
    )
    sra = CSVCharFilter(
        field_name="sra_ids__identifier", lookup_expr="icontains"
    )
    pubmed = CSVCharFilter(
        field_name="pubmed_ids__identifier", lookup_expr="icontains"
    )
    keyword = CSVCharFilter(
        field_name="keywords__text", lookup_expr="icontains"
    )

    first_name = CSVCharFilter(
        method="filter_contributor", lookup_expr="iexact"
    )
    last_name = CSVCharFilter(
        method="filter_contributor", lookup_expr="iexact"
    )
    username = CSVCharFilter(method="filter_contributor", lookup_expr="iexact")
    display_name = CSVCharFilter(method="filter_contributor_display_name")

    @staticmethod
    def split(value, sep=","):
        value = list(csv.reader([value], delimiter=sep))[0]
        if not isinstance(value, list):
            value = [value]
        return value

    @property
    def qs_or(self):
        """Patch in the ability for an OR search over all fields"""
        if not hasattr(self, "_qs_or"):
            if not self.is_bound:
                self._qs_or = self.queryset.all()
                return self._qs_or
            if not self.form.is_valid():
                if self.strict == constants.STRICTNESS.RAISE_VALIDATION_ERROR:
                    raise forms.ValidationError(self.form.errors)
                elif self.strict == constants.STRICTNESS.RETURN_NO_RESULTS:
                    self._qs_or = self.queryset.none()
                    return self._qs_or
                # else STRICTNESS.IGNORE...  ignoring
            # start with no results and filter from there
            qs = self.queryset.none()
            if not self.data:
                self._qs_or = self.queryset.all()
            else:
                for name, filter_ in self.filters.items():
                    value = self.form.cleaned_data.get(name)
                    if value:  # valid & clean data
                        qs |= filter_.filter(self.queryset, value)
                self._qs_or = qs
        return self._qs_or

    def contributor_model_ids(self, user, queryset=None):
        if queryset is None:
            queryset = self.qs
        model_class_name = queryset.model.__name__.lower()
        instance_group_names = (
            user.groups.filter(name__icontains=model_class_name)
        ).values_list("name", flat=True)
        ids = re.findall(digit_re, ",".join(instance_group_names))
        return ids

    def filter_for_user(self, user, qs=None):
        if qs is None:
            qs = self.qs

        private_visible_ids = []
        if user is not None:
            private_visible_ids = self.contributor_model_ids(user, qs)

        public = qs.filter(private=False)
        private = qs.filter(private=True).filter(id__in=private_visible_ids)
        return (public | private).distinct()

    def filter_contributor(self, queryset, name, value):
        model_ids = set()
        for v in self.split(value):
            users = User.objects.filter(**{name: v})
            for user in users:
                model_ids |= set(
                    self.contributor_model_ids(user, queryset=queryset)
                )
        return queryset.filter(id__in=model_ids)

    def filter_contributor_display_name(self, queryset, name, value):
        # FIXME: Optimize this. Remove triple for loop. Can make a new
        #  field on profile display_name that hoists credit-name from
        #  social_auth extra_data.
        instances_pks = []
        if not queryset.count():
            return queryset
        model = queryset.first().__class__
        for instance in queryset.all():
            for v in self.split(value):
                matches = any(
                    [
                        v.lower() in c.profile.get_display_name().lower()
                        for c in instance.contributors
                    ]
                )
                if matches:
                    instances_pks.append(instance.pk)
        return model.objects.filter(pk__in=set(instances_pks))


class ExperimentSetFilterModel(DatasetModelFilter):
    """
    Filter `ExperimentSets` based on the fields in `DatasetModelFilter`.
    """

    class Meta(DatasetModelFilter.Meta):
        model = models.experimentset.ExperimentSet


class ExperimentFilter(DatasetModelFilter):
    """
    Filter `Experiment` based on the fields in `DatasetModelFilter` plus
    additional fields on scoresets:
        - licence
        - target
        - organism
        - genome
        - uniprot
        - ensembl
        - refseq
    """

    LICENCE = "licence"
    TARGET = "target"
    ORGANISM = "organism"
    GENOME = "genome"
    UNIPROT = "uniprot"
    ENSEMBL = "ensembl"
    REFSEQ = "refseq"

    class Meta(DatasetModelFilter.Meta):
        model = models.experiment.Experiment
        fields = DatasetModelFilter.Meta.fields + (
            "licence",
            "genome",
            "target",
            "organism",
            "uniprot",
            "ensembl",
            "refseq",
        )

    licence = CSVCharFilter(method="filter_by_scoreset")
    genome = CSVCharFilter(method="filter_by_scoreset")
    target = CSVCharFilter(method="filter_by_scoreset")
    organism = CSVCharFilter(method="filter_by_scoreset")
    uniprot = CSVCharFilter(method="filter_by_scoreset")
    ensembl = CSVCharFilter(method="filter_by_scoreset")
    refseq = CSVCharFilter(method="filter_by_scoreset")
    target_type = CSVCharFilter(
        field_name="scoresets__target__category", lookup_expr="icontains"
    )

    def filter_by_scoreset(self, queryset, name, value):
        experiments = set()
        user = getattr(self.request, "user", None)
        scoresets = (
            ScoreSetFilter()
            .filters.get(name)
            .filter(qs=models.scoreset.ScoreSet.objects.all(), value=value)
        )
        for scoreset in scoresets:
            if scoreset.private:
                if user is not None and user in scoreset.contributors:
                    experiments.add(scoreset.parent.pk)
            else:
                experiments.add(scoreset.parent.pk)

        return queryset.filter(pk__in=experiments)


class ScoreSetFilter(DatasetModelFilter):
    """
    Filter `ScoreSet` based on the fields in `DatasetModelFilter` plus
    additional fields:
        - licence
        - target
        - organism
        - genome
        - uniprot
        - ensembl
        - refseq
        - data_usage_policy
    """

    LICENCE = "licence"
    TARGET = "target"
    ORGANISM = "organism"
    GENOME = "genome"
    UNIPROT = "uniprot"
    ENSEMBL = "ensembl"
    REFSEQ = "refseq"
    DATA_USAGE_POLICY = "data_usage_policy"
    TARGET_TYPE = "target_type"

    class Meta(DatasetModelFilter.Meta):
        model = models.scoreset.ScoreSet
        fields = DatasetModelFilter.Meta.fields + (
            "licence",
            "genome",
            "target",
            "organism",
            "uniprot",
            "ensembl",
            "refseq",
            "target_type",
            "data_usage_policy",
        )

    licence = CSVCharFilter(method="filter_licence")
    data_usage_policy = CSVCharFilter(
        field_name="data_usage_policy", lookup_expr="icontains"
    )
    genome = CSVCharFilter(method="filter_genome")
    target = CSVCharFilter(field_name="target__name", lookup_expr="icontains")
    organism = CSVCharFilter(
        field_name="target__reference_maps__genome__organism_name",
        lookup_expr="icontains",
    )
    uniprot = CSVCharFilter(
        field_name="target__uniprot_id__identifier", lookup_expr="iexact"
    )
    ensembl = CSVCharFilter(
        field_name="target__ensembl_id__identifier", lookup_expr="iexact"
    )
    refseq = CSVCharFilter(
        field_name="target__refseq_id__identifier", lookup_expr="iexact"
    )
    target_type = CSVCharFilter(
        field_name="target__category", lookup_expr="icontains"
    )

    def filter_licence(self, queryset, name, value):
        q = Q()
        for v in self.split(value):
            q |= Q(licence__short_name__icontains=v) | Q(
                licence__long_name__icontains=v
            )
        return queryset.filter(q)

    def filter_genome(self, queryset, name, value):
        genome_field = "target__reference_maps__genome"
        short_name = "{}__short_name__iexact".format(genome_field)
        assembly_id = "{}__genome_id__identifier__iexact".format(genome_field)
        q = Q()
        for v in self.split(value):
            q |= Q(**{short_name: v}) | Q(**{assembly_id: v})
        return queryset.filter(q)
