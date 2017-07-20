
import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse

from crispy_forms import layout
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Field, Submit, HTML


from .models import Experiment
from .utils.query_parsing import parse_query


class BasicSearchForm(forms.Form):
    column_search = forms.CharField(
        label=None,
        max_length=None,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Examples: BRCA1; Kinase; "
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
        forms.Form.clean(self)
        queries = parse_query(self.data['column_search'])
        self.cleaned_data['column_search'] = queries
        return self.cleaned_data

    def query_experiments(self):
        queries = self.cleaned_data.get('column_search', None)
        entries = Experiment.objects.none()
        if not queries:
            return entries

        for accession in queries:
            entries |= Experiment.objects.all().filter(
                accession__iexact=accession)

        for target in queries:
            entries |= Experiment.objects.all().filter(
                target__iexact=target)

        for author in queries:
            entries |= Experiment.objects.all().filter(
                authors__icontains=author)

        for target_org in queries:
            entries |= Experiment.objects.all().filter(
                target_organism__icontains=target_org)

        for alt_accesion in queries:
            entries |= Experiment.objects.all().filter(
                alt_target_accessions__icontains=alt_accesion)

        for wt_sequence in queries:
            entries |= Experiment.objects.all().filter(
                wt_sequence__iexact=wt_sequence)

        for keyword in queries:
            entries |= Experiment.objects.all().filter(
                keywords__icontains=keyword)
            entries |= Experiment.objects.all().filter(
                abstract__icontains=keyword)
            entries |= Experiment.objects.all().filter(
                short_description__icontains=keyword)
            entries |= Experiment.objects.all().filter(
                method_description__icontains=keyword)

        return entries


class AdvancedSearchForm(forms.ModelForm):
    class Meta:
        model = Experiment
        exclude = (
            "date", "abstract",
            "short_description", "method_description"
        )

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

        for key, text in Experiment.placeholder_text.items():
            self.fields[key].widget = forms.TextInput(
                attrs={'placeholder': text})

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
                    Field('authors'),
                    css_class="col-sm-6 col-md-6 col-lg-6"),
                Div(
                    Field('date_from'),
                    css_class="col-sm-3 col-md-3 col-lg-3"),
                Div(
                    Field('date_to'),
                    css_class="col-sm-3 col-md-3 col-lg-3"),
                css_class="row"
            ),
            Div(
                Div(
                    Field('target_organism'),
                    css_class="col-sm-6 col-md-6 col-lg-6"),
                Div(
                    Field('alt_target_accessions'),
                    css_class="col-sm-6 col-md-6 col-lg-6"),
                css_class="row"
            ),
            Div(
                Div(
                    Field('wt_sequence'),
                    css_class="col-sm-6 col-md-6 col-lg-6"),
                css_class="row"
            ),
            Div(
                Submit(name="search", value='Search'),
                css_class="row pull-right"
            ),
        )

    def clean(self):
        forms.ModelForm.clean(self)
        try:
            date_from = self.cleaned_data['date_from']
            date_to = self.cleaned_data['date_to']
        except KeyError:
            raise ValidationError("Enter a valid date.")

        if date_to is not None and date_from is not None:
            if date_to < date_from:
                msg = "Must be on or before the from date."
                self._errors["date_to"] = self.error_class([msg])

        def clean_str(field, sep=','):
            return parse_query(self.cleaned_data[field], sep)
        
        try:
            self.cleaned_data["accession"] = clean_str("accession")
            self.cleaned_data["target"] = clean_str("target")
            self.cleaned_data["keywords"] = clean_str("keywords")
            self.cleaned_data["authors"] = clean_str("authors")
            self.cleaned_data["target_organism"] = clean_str("target_organism")
            self.cleaned_data["alt_target_accessions"] = clean_str("alt_target_accessions")
            self.cleaned_data["wt_sequence"] = clean_str("wt_sequence")
        except Exception as e:
            raise ValidationError(e)
        return self.cleaned_data

    def query_experiments(self):
        experiments = Experiment.objects.all()

        accesions = self.cleaned_data.get("accession", None)
        if accesions:
            entries = Experiment.objects.none()
            for accession in accesions:
                entries |= Experiment.objects.all().filter(
                    accession__iexact=accession)
            experiments &= entries

        targets = self.cleaned_data.get("target", None)
        if targets:
            entries = Experiment.objects.none()
            for target in targets:
                entries |= Experiment.objects.all().filter(
                    target__iexact=target)
            experiments &= entries

        authors = self.cleaned_data.get("authors", None)
        if authors:
            entries = Experiment.objects.none()
            for author in authors:
                entries |= Experiment.objects.all().filter(
                    authors__icontains=author)
            experiments &= entries

        target_organisms = self.cleaned_data.get("target_organism", None)
        if target_organisms:
            entries = Experiment.objects.none()
            for org in target_organisms:
                entries |= Experiment.objects.all().filter(
                    target_organism__icontains=org)
            experiments &= entries

        alt_target_accessions = self.cleaned_data.get(
            "alt_target_accessions", None)
        if alt_target_accessions:
            entries = Experiment.objects.none()
            for alt in alt_target_accessions:
                entries |= Experiment.objects.all().filter(
                    alt_target_accessions__icontains=alt)
            experiments &= entries

        wt_sequences = self.cleaned_data.get("wt_sequence", None)
        if wt_sequences:
            entries = Experiment.objects.none()
            for wt_sequence in wt_sequences:
                entries |= Experiment.objects.all().filter(
                    wt_sequence__iexact=wt_sequence)
            experiments &= entries

        keywords = self.cleaned_data.get("keywords", None)
        if keywords:
            entries = Experiment.objects.none()
            for keyword in keywords:
                entries |= Experiment.objects.all().filter(
                    keywords__icontains=keyword)
                entries |= Experiment.objects.all().filter(
                    abstract__icontains=keyword)
                entries |= Experiment.objects.all().filter(
                    short_description__icontains=keyword)
                entries |= Experiment.objects.all().filter(
                    method_description__icontains=keyword)
            experiments &= entries

        date_from = self.cleaned_data.get("date_from", None)
        if date_from:
            experiments = experiments.filter(date__gte=date_from)

        date_to = self.cleaned_data.get("date_to", None)
        if date_to:
            experiments = experiments.filter(date__lte=date_to)

        return experiments


class ExperimentCreationForm(forms.Form):
    """
    Prototype form for creating a new experiment.
    """
    # --------------------Model/Field Declaration --------------------------- #
    author = forms.CharField(
        label="Author(s)", required=True,
        widget=forms.TextInput(
            attrs=dict(placeholder='Comma separated.')))
    target = forms.CharField(label="Target", required=True)
    wt_seq = forms.CharField(
        label="Wild-type sequence", required=True,
        widget=forms.Textarea(attrs=dict(rows=4)))
    model = forms.CharField(label="Target organism", required=False)
    keywords = forms.CharField(
        label="Keywords", required=False,
        widget=forms.TextInput(
            attrs=dict(placeholder='Comma separated.')))
    protein = forms.CharField(
        label="Accessions", required=False,
        widget=forms.TextInput(
            attrs=dict(placeholder='UniProt, RefSeq, ...')))
    abstract = forms.CharField(
        label="Abstract", required=False,
        widget=forms.Textarea(attrs=dict(placeholder='Markdown is supported')))
    short_description = forms.CharField(
        label="Short Description", required=False, max_length=512,
        widget=forms.Textarea(attrs=dict(
            placeholder='Markdown is supported', rows=2)))


    # -------------------------- Methods ------------------------------------ #
    def __init__(self, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'crispy_experiment_form'
        self.helper.form_show_labels = True
        self.helper.form_method = "POST"
        self.helper.form_action = reverse('main:new_experiment')
        self.helper.layout = Layout(
            Div(Field("author")),
            Div(
                Div(Field('target'), css_class="col-sm-6 col-md-6 col-lg-6"),
                Div(Field('protein'), css_class="col-sm-6 col-md-6 col-lg-6"),
                css_class="row"
            ),
            Div(Field("wt_seq")),
            Div(
                Div(Field('model'), css_class="col-sm-6 col-md-6 col-lg-6"),
                Div(Field('keywords'), css_class="col-sm-6 col-md-6 col-lg-6"),
                css_class="row"
            ),
            Div(Field("abstract")),
            Div(Field("short_description")),
            Div(Submit(name="submit", value='Next'), css_class="pull-right")
        )


class ScoresetCreationForm(forms.Form):
    """
    Prototype form for creating a new experiment.
    """
    # --------------------Model/Field Declaration --------------------------- #
    exp_accession = forms.CharField(
        label="Experiment accession", required=True,
        widget=forms.TextInput(attrs=dict(value="")))
    authors = forms.CharField(label="Author(s)", required=True)
    name = forms.CharField(label="Score set name", required=False)
    description = forms.CharField(
        label="Description", required=False,
        widget=forms.Textarea(
            attrs=dict(placeholder='Markdown supported.', rows=3)))
    theory = forms.CharField(
        label="Method theory", required=False,
        widget=forms.Textarea(
            attrs=dict(placeholder='MathJax supported.', rows=3)))
    keywords = forms.CharField(
        label="Keywords", required=False,
        widget=forms.TextInput(
            attrs=dict(placeholder='Comma separated.')))
    data = forms.CharField(
        label="Dataset (header required)", required=True,
        widget=forms.Textarea(attrs=dict(
            placeholder='hgvs,score,SE, <optional additional columns>, ...',
            rows=10)))

    # -------------------------- Methods ------------------------------------ #
    def __init__(self, accession=None, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'crispy_scoreset_form'
        self.helper.form_show_labels = True
        self.helper.form_method = "POST"
        self.helper.form_action = reverse("main:new_scoreset")

        if accession is not None:
            field = self.fields['exp_accession']
            field.widget.attrs['value'] = accession

        self.helper.layout = Layout(
            Div(Field("exp_accession")),
            Div(Field("authors")),
            Div(
                Div(Field('name'), css_class="col-sm-6 col-md-6 col-lg-6"),
                Div(Field('keywords'), css_class="col-sm-6 col-md-6 col-lg-6"),
                css_class="row"
            ),
            Div(Field("description")),
            Div(Field("theory")),
            Field("data"),
            HTML("<p><b>Note:</b> Dataset must include a header line.</p>"),
            Div(Submit(name="submit", value='Submit'), css_class="pull-right")
        )
