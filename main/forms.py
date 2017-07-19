
import re
import shlex

from django import forms
from django.db import models
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse

from crispy_forms.helper import FormHelper
from crispy_forms import layout
from crispy_forms.layout import Layout, Div, Field, Submit


from .models import Experiment
from .utils.query_parsing import parse_query


class BasicSearchForm(forms.Form):
    column_search = forms.CharField(
        label=None,
        max_length=None,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Examples: BRCA1; Kinase; " \
                "EXP0001HSA, 'quoted single-string query', ..."
        })
    )

    def __init__(self, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'crispy_basic_search'
        self.helper.form_show_labels = False
        self.helper.form_method = "POST"
        self.helper.form_action = reverse("main:basic_search")

    def clean(self):
        queries = parse_query(self.data['column_search'])
        self.cleaned_data['column_search'] = queries
        return self.cleaned_data

    def query_experiments(self):
        queries = self.cleaned_data['column_search']
        entries = Experiment.objects.none()

        for accession in queries:
            entries |= Experiment.objects.all().filter(
                accession__iexact=accession)

        for target in queries:
            entries |= Experiment.objects.all().filter(
                target__iexact=target)

        for author in queries:
            entries |= Experiment.objects.all().filter(
                author__icontains=author)

        for reference in queries:
            entries |= Experiment.objects.all().filter(
                reference__icontains=reference)

        for alt_reference in queries:
            entries |= Experiment.objects.all().filter(
                alt_reference__icontains=alt_reference)

        for scoring_method in queries:
            entries |= Experiment.objects.all().filter(
                scoring_method__icontains=scoring_method)

        for keyword in queries:
            entries |= Experiment.objects.all().filter(
                keywords__icontains=keyword)
            entries |= Experiment.objects.all().filter(
                description__icontains=keyword)

        return entries


class AdvancedSearchForm(forms.ModelForm):
    class Meta:
        model = Experiment
        exclude = ("date", "description")

    date_from = forms.DateField(
        label="Date from:",
        required=False,
        widget=forms.DateInput(attrs={"placeholder": "yyyy-mm-dd"})
    )
    date_to = forms.DateField(
        label="Date to:",
        required=False,
        widget=forms.DateInput(attrs={"placeholder": "yyyy-mm-dd"})
    )

    def __init__(self, *args, **kwargs):
        forms.ModelForm.__init__(self, *args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "POST"
        self.helper.form_action = reverse("main:advanced_search")
        self.helper.form_id = 'crispy_advanced_search'
        for key in self.fields:
            self.fields[key].required = False

        self.fields['accession'].widget = \
            forms.TextInput(attrs={'placeholder': "EXP0001HSA"})
        self.fields['target'].widget = \
            forms.TextInput(attrs={'placeholder': "BRCA1"})
        self.fields['author'].widget = \
            forms.TextInput(
                attrs={'placeholder': "Aurhor 1, Author 2, ..."})
        self.fields['reference'].widget = \
            forms.TextInput(
                attrs={'placeholder': "Homo sapiens, Mus musculus, ..."})
        self.fields['alt_reference'].widget = \
            forms.TextInput(attrs={'placeholder': "Homo sapiens"})
        self.fields['scoring_method'].widget = \
            forms.TextInput(
                attrs={'placeholder': "OLS regression, Log ratios, ..."})
        self.fields['keywords'].widget = \
            forms.TextInput(attrs={'placeholder': "Kinase, DNA Repair, ..."})

        self.helper.layout = Layout(
            Div(
                Div(
                    Field('accession'),
                    css_class="col-sm-3 col-md-3 col-lg-3"),
                Div(
                    Field('target'),
                    css_class="col-sm-3 col-md-3 col-lg-3"),
                Div(
                    Field('keywords'),
                    css_class="col-sm-6 col-md-6 col-lg-6"),
                css_class="row"
            ),
            Div(
                Div(
                    Field('author'),
                    css_class="col-sm-6 col-md-6 col-lg-6"),
                Div(
                    Field('date_from'),
                    css_class="col-sm-2 col-md-2 col-lg-2"),
                Div(
                    Field('date_to'),
                    css_class="col-sm-2 col-md-2 col-lg-2"),
                css_class="row"
            ),
            Div(
                Div(
                    Field('reference'),
                    css_class="col-sm-6 col-md-6 col-lg-6"),
                Div(
                    Field('alt_reference'),
                    css_class="col-sm-6 col-md-6 col-lg-6"),
                css_class="row"
            ),
            Div(
                Div(
                    Field('scoring_method'),
                    css_class="col-sm-6 col-md-6 col-lg-6"),
                css_class="row"
            ),
            Div(
                Div(
                    Field('num_variants'),
                    css_class="col-sm-3 col-md-3 col-lg-3"),
                css_class="row"
            ),
            Div(
                Submit(name="search", value='Search'),
                css_class="row pull-right"
            ),
        )

    def clean(self):
        date_from = self.cleaned_data['date_from']
        date_to = self.cleaned_data['date_to']

        if date_to is not None and date_from is not None:
            if date_to < date_from:
                msg = "Must be on or before the from date."
                self._errors["date_to"] = self.error_class([msg])

        def clean_str(field, sep=','):
            return parse_query(self.cleaned_data[field], sep)
        
        try:
            self.cleaned_data["keywords"] = clean_str("keywords")
            self.cleaned_data["target"] = clean_str("target")
            self.cleaned_data["accession"] = clean_str("accession")
            self.cleaned_data["author"] = clean_str("author")
            self.cleaned_data["reference"] = clean_str("reference")
            self.cleaned_data["alt_reference"] = clean_str("alt_reference")
            self.cleaned_data["scoring_method"] = clean_str("scoring_method")
        except Exception as e:
            raise ValidationError(e)
        return self.cleaned_data

    def query_experiments(self):
        experiments = Experiment.objects.all()

        accesions = self.cleaned_data["accession"]
        if accesions:
            entries = Experiment.objects.none()
            for accession in accesions:
                entries |= Experiment.objects.all().filter(
                    accession__iexact=accession)
            experiments &= entries

        targets = self.cleaned_data["target"]
        if targets:
            entries = Experiment.objects.none()
            for target in targets:
                entries |= Experiment.objects.all().filter(
                    target__iexact=target)
            experiments &= entries

        authors = self.cleaned_data["author"]
        if authors:
            entries = Experiment.objects.none()
            for author in authors:
                entries |= Experiment.objects.all().filter(
                    author__icontains=author)
            experiments &= entries

        references = self.cleaned_data["reference"]
        if references:
            entries = Experiment.objects.none()
            for reference in references:
                entries |= Experiment.objects.all().filter(
                    reference__icontains=reference)
            experiments &= entries

        alt_references = self.cleaned_data["alt_reference"]
        if alt_references:
            entries = Experiment.objects.none()
            for alt_reference in alt_references:
                entries |= Experiment.objects.all().filter(
                    alt_reference__icontains=alt_reference)
            experiments &= entries

        scoring_methods = self.cleaned_data["scoring_method"]
        if scoring_methods:
            entries = Experiment.objects.none()
            for scoring_method in scoring_methods:
                entries |= Experiment.objects.all().filter(
                    scoring_method__icontains=scoring_method)
            experiments &= entries

        keywords = self.cleaned_data["keywords"]
        if keywords:
            entries = Experiment.objects.none()
            for keyword in keywords:
                entries |= Experiment.objects.all().filter(
                    keywords__icontains=keyword)
                entries |= Experiment.objects.all().filter(
                    description__icontains=keyword)
            experiments &= entries

        num_variants = self.cleaned_data["num_variants"]
        experiments = experiments.filter(num_variants__gte=num_variants)

        date_from = self.cleaned_data["date_from"]
        if date_from:
            experiments = experiments.filter(date__gte=date_from)

        date_to = self.cleaned_data["date_to"]
        if date_to:
            experiments = experiments.filter(date__lte=date_to)

        return experiments


class ExperimentCreationForm(forms.Form):
    """
    Prototype form for creating a new experiment.
    """
    # --------------------Model/Field Declaration --------------------------- #

    # -------------------------- Methods ------------------------------------ #
    def __init__(self, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'crispy_experiment_form'
        self.helper.form_show_labels = True
        self.helper.form_method = "POST"
        self.helper.form_action = reverse("main:new_experiment")


class ScoresetCreationForm(forms.Form):
    """
    Prototype form for creating a new experiment.
    """
    # --------------------Model/Field Declaration --------------------------- #

    # -------------------------- Methods ------------------------------------ #
    def __init__(self, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'crispy_scoreset_form'
        self.helper.form_show_labels = True
        self.helper.form_method = "POST"
        self.helper.form_action = reverse("main:new_scoreset")
