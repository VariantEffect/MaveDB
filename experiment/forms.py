

import django.forms as forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

from .models import Experiment, ExperimentSet


class ExperimentForm(forms.ModelForm):

    class Meta:
        model = Experiment
        fields = (
            'experimentset',
            'private',
            'target',
            'wt_sequence',
            'abstract',
            'method_desc',
            'sra_id',
            'doi_id'
        )

    def clean(self):
        cleaned_data = super(ExperimentForm, self).clean()
        experimentset = cleaned_data.get("experimentset", None)
        if experimentset is None:
            self.add_error(
                "experimentset",
                ValidationError(
                    _("Please select a valid experiment set accession.")
                )
            )
        return cleaned_data
