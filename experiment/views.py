from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.views.generic import DetailView, FormView
from django.forms import formset_factory
from django.core.exceptions import ObjectDoesNotExist

from main.forms import (
    KeywordForm, ExternalAccessionForm,
    ReferenceMappingForm, TargetOrganismForm
)

from main.models import (
    Keyword, ExternalAccession,
    TargetOrganism, ReferenceMapping
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


def parse_text_formset(formset, model_class, prefix):
    objects = []
    for i, form in enumerate(formset):
        text = form.data.get("{}-{}-text".format(prefix, i), "")
        try:
            model = model_class.objects.get(text=text)
            objects.append(model)
        except ObjectDoesNotExist:
            if form.is_valid():
                if form.cleaned_data:
                    model = form.save(commit=False)
                    objects.append(model)
            else:
                objects.append(None)
    return objects


def parse_mapping_formset(reference_mapping_formset):
    objects = []
    for i, form in enumerate(reference_mapping_formset):
        if form.is_valid():
            if form.cleaned_data:
                model = form.save(commit=False)
                objects.append(model)
        else:
            objects.append(None)
    return objects


def experiment_create_view(request):
    context = {}
    experiment_form = ExperimentForm(prefix="experiment")
    keyword_formset = KeywordFormSet(prefix="keyword")
    external_accession_formset = ExternalAccessionFormSet(
        prefix="external_accession"
    )
    ref_mapping_formset = ReferenceMappingFormSet(
        prefix="ref_mapping"
    )
    context["experiment_form"] = experiment_form
    context["keyword_formset"] = keyword_formset
    context["external_accession_formset"] = external_accession_formset
    context["ref_mapping_formset"] = ref_mapping_formset

    # If you change the prefix arguments here, make sure to change them
    # in the corresponding template element id fields as well. If you don't,
    # expect everything to break horribly. You've been warned.
    if request.method == "POST":
        experiment_form = ExperimentForm(request.POST, prefix="experiment")
        keyword_formset = KeywordFormSet(request.POST, prefix="keyword")
        external_accession_formset = ExternalAccessionFormSet(
            request.POST, prefix="external_accession"
        )
        ref_mapping_formset = ReferenceMappingFormSet(
            request.POST, prefix="ref_mapping"
        )
        context["experiment_form"] = experiment_form
        context["keyword_formset"] = keyword_formset
        context["external_accession_formset"] = external_accession_formset
        context["ref_mapping_formset"] = ref_mapping_formset

        if experiment_form.is_valid():
            experiment = experiment_form.save(commit=False)
        else:
            return render(
                request,
                "experiment/new_experiment.html",
                context=context
            )

        keywords = parse_text_formset(keyword_formset, Keyword, "keyword")
        if not all([k is not None for k in keywords]):
            return render(
                request,
                "experiment/new_experiment.html",
                context=context
            )

        accessions = parse_text_formset(
            external_accession_formset,
            ExternalAccession, "external_accession"
        )
        if not all([a is not None for a in accessions]):
            return render(
                request,
                "experiment/new_experiment.html",
                context=context
            )

        maps = parse_mapping_formset(ref_mapping_formset)
        if not all([m is not None for m in maps]):
            return render(
                request,
                "experiment/new_experiment.html",
                context=context
            )

        # Get target organism data
        target_organism = experiment_form.cleaned_data.get(
            "target_organism", "")
        if target_organism:
            try:
                target_organism = TargetOrganism.objects.get(
                    text=target_organism)
            except ObjectDoesNotExist:
                target_organism = TargetOrganism(text=target_organism)
        else:
            target_organism = None

        # Looks like everything is good to save
        experiment.save()
        if target_organism is not None:
            target_organism.save()
            experiment.target_organism.add(target_organism)

        for kw in keywords:
            kw.save()
            experiment.keywords.add(kw)

        for acc in accessions:
            acc.save()
            experiment.external_accessions.add(acc)

        for ref_map in maps:
            ref_map.experiment = experiment
            ref_map.save()

        experiment.save()
        accession = experiment.accession
        return redirect("experiment:experiment_detail", accession=accession)

    else:
        return render(
            request,
            "experiment/new_experiment.html",
            context=context
        )
