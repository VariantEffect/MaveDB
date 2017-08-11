from django.shortcuts import render
from django.views.generic import DetailView

from .models import Experiment, ExperimentSet
from .forms import ExperimentForm


class ExperimentDetailView(DetailView):
    model = Experiment
    template_name = 'experiment.html'

    def get_object(self):
        print(self.request)
