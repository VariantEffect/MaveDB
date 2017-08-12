from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.views.generic import DetailView, FormView
from django.forms import formset_factory

from main.forms import (
    KeywordForm, ExternalAccessionForm,
    ReferenceMappingForm, TargetOrganismForm
)

from .models import Experiment, ExperimentSet
from .forms import ExperimentForm

KeywordFormSet = formset_factory(KeywordForm)
ExternalAccessionFormSet = formset_factory(ExternalAccessionForm)
ReferenceMappingFormSet = formset_factory(ReferenceMappingForm)


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


def experiment_create_view(request):
    context = {}

    # If you change the prefix arguments here, make sure to change them
    # in the corresponding template element id fields as well. If you don't,
    # expect everything to break horribly. You've been warned.
    if request.method == "POST":
        context["experiment_form"] = ExperimentForm(
            request.POST, prefix="experiment"
        )
        context["keyword_formset"] = KeywordFormSet(
            request.POST, prefix="keyword"
        )
        context["external_accession_formset"] = ExternalAccessionFormSet(
            request.POST, prefix="external_accession"
        )
        context["ref_mapping_formset"] = ReferenceMappingFormSet(
            request.POST, prefix="ref_mapping"
        )
    else:
        context["experiment_form"] = ExperimentForm(
            prefix="experiment"
        )
        context["keyword_formset"] = KeywordFormSet(
            prefix="keyword"
        )
        context["external_accession_formset"] = ExternalAccessionFormSet(
            prefix="external_accession"
        )
        context["ref_mapping_formset"] = ReferenceMappingFormSet(
            prefix="ref_mapping"
        )

    print(context["keyword_formset"].__dict__)
    return render(
        request,
        "experiment/new_experiment.html",
        context=context
    )
