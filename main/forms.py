from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms import layout
from crispy_forms.layout import Layout, Div, Field, Submit


from .models import Experiment


class BasicSearchForm(forms.Form):
    column_search = forms.CharField(
        label=None,
        max_length=None,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Examples: BRCA1; Kinase; EXP0001HSA..."
        })
    )

    def __init__(self, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'crispy_basic_search'
        self.helper.form_show_labels = False


class AdvancedSearchForm(forms.Form):
    accessions = forms.CharField(
        label="Accession:",
        max_length=None,
        strip=True,
        required=False,
        widget=forms.TextInput(attrs={'style': 'width:100%;'})
    )
    targets = forms.CharField(
        label="Targets:",
        max_length=None,
        strip=True,
        required=False,
        widget=forms.TextInput(attrs={'style': 'width:100%;'})
    )
    keywords = forms.CharField(
        label="Keywords:",
        max_length=None,
        strip=True,
        required=False,
        widget=forms.TextInput(attrs={'style': 'width:100%;'})
    )
    
    authors = forms.CharField(
        label="Authors:",
        max_length=None,
        strip=True,
        required=False,
        widget=forms.TextInput(attrs={'style': 'width:100%;'})
    )
    date_from = forms.DateField(
        label="Date from:",
        required=False,
        widget=forms.DateInput()
    )
    date_to = forms.DateField(
        label="Date to:",
        required=False,
        widget=forms.DateInput()
    )

    primary_references = forms.CharField(
        label="References:",
        max_length=None,
        strip=True,
        required=False,
        widget=forms.TextInput(attrs={'style': 'width:100%;'})
    )   
    secondary_references = forms.CharField(
        label="Secondary references:",
        max_length=None,
        strip=True,
        required=False,
        widget=forms.TextInput(attrs={'style': 'width:100%;'})
    )

    scoring_methods = forms.CharField(
        label="Scoring methods:",
        max_length=None,
        strip=True,
        required=False,
        widget=forms.TextInput()
    )

    min_avg_read_depth = forms.IntegerField(
        label="Average read depth from:",
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={'value': 1})
    )
    min_avg_base_coverage = forms.IntegerField(
        label="Average coverage from:",
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={'value': 1})
    )
    min_variant_count = forms.IntegerField(
        label="Variant count from:",
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={'value': 1})
    )

    def __init__(self, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "POST"
        self.helper.form_id = 'crispy_advanced_search'

        self.helper.layout = Layout(
            Div(
                Div(Field('accessions'), css_class="col-sm-3 col-md-3 col-lg-3"),
                Div(Field('targets'), css_class="col-sm-3 col-md-3 col-lg-3"),
                Div(Field('keywords'), css_class="col-sm-6 col-md-6 col-lg-6"),
                css_class="row"
            ),
            Div(
                Div(Field('authors'), css_class="col-sm-6 col-md-6 col-lg-6"),
                Div(Field('date_from'), css_class="col-sm-2 col-md-2 col-lg-2"),
                Div(Field('date_to'), css_class="col-sm-2 col-md-2 col-lg-2"),
                css_class="row"
            ),
            Div(
                Div(Field('primary_references'), css_class="col-sm-6 col-md-6 col-lg-6"),
                Div(Field('secondary_references'), css_class="col-sm-6 col-md-6 col-lg-6"),
                css_class="row"
            ),
            Div(
                Div(Field('scoring_methods'), css_class="col-sm-6 col-md-6 col-lg-6"),
                css_class="row"
            ),
            Div(
                Div(Field('min_avg_read_depth'), css_class="col-sm-3 col-md-3 col-lg-3"),
                Div(Field('min_avg_base_coverage'), css_class="col-sm-3 col-md-3 col-lg-3"),
                Div(Field('min_variant_count'), css_class="col-sm-3 col-md-3 col-lg-3"),
                css_class="row"
            ),
            Div(
                Submit(name="search", value='Search'),
                css_class="row pull-right"
            ),
        )
