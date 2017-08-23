

import django.forms as forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

from main.models import ExternalAccession, Keyword

from .models import Experiment, ExperimentSet


class ExperimentForm(forms.ModelForm):
    """
    Docstring
    """
    class Meta:
        model = Experiment
        fields = (
            'experimentset',
            'private',
            'target',
            'target_organism',
            'wt_sequence',
            'abstract',
            'method_desc',
            'sra_id',
            'doi_id'
        )

    target_organism = forms.CharField(required=False, max_length=None)


class ExperimentEditForm(forms.ModelForm):
    """
    Docstring
    """
    class Meta:
        model = Experiment
        fields = (
            'private',
            'doi_id',
            'keywords',
            'external_accessions',
            'abstract',
            'method_desc'
        )

    # Additional fields for M2M relationships.
    # ---------------------------------------------------------------------- #
    keywords = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.widgets.SelectMultiple(
            attrs={
                "class": "select2 select2-token-select",
                "style": "width:100%;height:50px;"
            }
        )
    )

    external_accessions = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        widget=forms.widgets.SelectMultiple(
            attrs={
                "class": "select2 select2-token-select",
                "style": "width:100%;height:50px;"
            }
        )
    )

    # Methods
    # ---------------------------------------------------------------------- #
    def __init__(self, *args, **kwargs):
        super(ExperimentEditForm, self).__init__(*args, **kwargs)
        self.keywords = []
        self.ext_accessions = []
        self.fields["keywords"].queryset = Keyword.objects.all()
        self.fields["external_accessions"].queryset = \
            ExternalAccession.objects.all()
        self.fields["abstract"].widget = forms.Textarea(
            attrs={"style": "height:250px;width:100%"}
        )
        self.fields["method_desc"].widget = forms.Textarea(
            attrs={"style": "height:250px;width:100%"}
        )

    def clean(self):
        cleaned_data = super(ExperimentEditForm, self).clean()
        keywords = cleaned_data.get("keywords", None)
        ext_accessions = cleaned_data.get("external_accessions", None)

        if keywords is None and self.errors["keywords"]:
            keywords_pks = self.data.getlist("keywords")
            keyword_ls = Keyword.parse_pk_list(keywords_pks)
            cleaned_data["keywords"] = keyword_ls
            self.errors.pop("keywords")
            self.keywords = keyword_ls

        if ext_accessions is None and self.errors["external_accessions"]:
            ext_accession_pks = self.data.getlist("external_accessions")
            ext_accession_ls = ExternalAccession.parse_pk_list(accession_pks)
            cleaned_data["external_accessions"] = ext_accession_ls
            self.errors.pop("external_accessions")
            self.keyext_accessionswords = ext_accession_ls

        return cleaned_data
