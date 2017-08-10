
import django.forms as forms

from .models import Experiment, ExperimentSet


class ExperimentForm(forms.ModelForm):

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
