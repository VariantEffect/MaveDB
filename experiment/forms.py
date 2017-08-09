
import django.forms as forms

from .models import Experiment, ExperimentSet


class ExperimentForm(forms.ModelForm):
    keywords = forms.CharField(
        required=False, max_length=1024, verbose_name="Keywords")
    external_accessions = forms.CharField(
        required=False, max_length=1024, verbose_name="External Accessions")
    target_organism = forms.CharField(
        required=False, max_length=1024, verbose_name="Target Organism")

    class Meta:
        model = Experiment
        fields = (
            'experimentset',
            'private',
            'wt_sequence',
            'target',
            'abstract',
            'method_desc',
            'sra_id',
            'doi_id'
        )
