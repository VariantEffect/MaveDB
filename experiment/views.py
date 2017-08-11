from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.views.generic import DetailView, FormView

from .models import Experiment, ExperimentSet
from .forms import ExperimentForm


class ExperimentDetailView(DetailView):
    model = Experiment
    template_name = 'experiment/experiment.html'
    context_object_name = "experiment"

    def get_object(self):
        accession = self.kwargs.get('accession', None)
        return get_object_or_404(Experiment, accession=accession)


class ExperimentSetDetailView(DetailView):
    model = ExperimentSet
    template_name = 'experiment/experimentset.html'
    context_object_name = "experimentset"

    def get_object(self):
        accession = self.kwargs.get('accession', None)
        return get_object_or_404(ExperimentSet, accession=accession)


class ExperimentCreateView(FormView):
    template_name = 'experiment/new_experiment.html'
    form_class = ExperimentForm

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        print(form.is_valid())
        print(form.cleaned_data)
        if not form.is_valid():
            return redirect("experiment:experiment_new", form=form)
