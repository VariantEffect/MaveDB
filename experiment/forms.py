

import django.forms as forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

from .models import Experiment, ExperimentSet


class ExperimentForm(forms.ModelForm):
    target_organism = forms.CharField(required=False, max_length=None)

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
