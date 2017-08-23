
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseForbidden, Http404
from django.core.urlresolvers import reverse_lazy
from django.views.generic import DetailView
from django.forms import formset_factory
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required

from main.forms import (
    KeywordForm, ExternalAccessionForm,
    ReferenceMappingForm, TargetOrganismForm
)

from accounts.permissions import (
    assign_user_as_instance_admin, PermissionTypes
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


EXPERIMENT_FORM_PREFIX = "experiment"
KEYWORD_FORM_PREFIX = "keyword"
EXTERNAL_ACCESSION_FORM_PREFIX = "external_accession"
REFERENCE_MAPPING_FORM_PREFIX = "reference_mapping"


class ExperimentDetailView(DetailView):
    """
    object in question and render a simple template for public viewing, or
    Simple class-based detail view for an `Experiment`. Will either find the
    404.

    Parameters
    ----------
    accession : `str`
        The accession of the `Experiment` to render.
    """
    model = Experiment
    template_name = 'experiment/experiment.html'
    context_object_name = "experiment"

    def dispatch(self, request, *args, **kwargs):
        try:
            experiment = self.get_object()
        except Http404:
            response = render(
                request=request,
                template_name="main/404_not_found.html"
            )
            response.status_code = 404
            return response

        has_permission = self.request.user.has_perm(
            PermissionTypes.CAN_VIEW, experiment)
        if experiment.private and not has_permission:
            response = render(
                request=request,
                template_name="main/403_forbidden.html",
                context={"instance": experiment},
            )
            response.status_code = 403
            return response
        else:
            return super(ExperimentDetailView, self).dispatch(
                request, *args, **kwargs
            )

    def get_object(self):
        accession = self.kwargs.get('accession', None)
        return get_object_or_404(Experiment, accession=accession)


class ExperimentSetDetailView(DetailView):
    """
    Simple class-based detail view for an `ExperimentSet`. Will either find the
    object in question and render a simple template for public viewing, or
    404.

    Parameters
    ----------
    accession : `str`
        The accession of the `ExperimentSet` to render.
    """
    model = ExperimentSet
    template_name = 'experiment/experimentset.html'
    context_object_name = "experimentset"

    def dispatch(self, request, *args, **kwargs):
        try:
            experimentset = self.get_object()
        except Http404:
            response = render(
                request=request,
                template_name="main/404_not_found.html"
            )
            response.status_code = 404
            return response

        has_permission = self.request.user.has_perm(
            PermissionTypes.CAN_VIEW, experimentset)
        if experimentset.private and not has_permission:
            response = render(
                request=request,
                template_name="main/403_forbidden.html",
                context={"instance": experimentset},
            )
            response.status_code = 403
            return response
        else:
            return super(ExperimentSetDetailView, self).dispatch(
                request, *args, **kwargs
            )

    def get_object(self):
        accession = self.kwargs.get('accession', None)
        return get_object_or_404(ExperimentSet, accession=accession)


def parse_text_formset(formset, model_class, prefix="formset"):
    """
    Utility function to parse a formset with a `text` attribute. Parses a
    formset into a list of instantiated but not commited models. Will only
    create a new model if the text attribute doesn't already exist in the
    database. If the form is not valid for a particular model, then `None`
    is appended to the list.

    Parameters
    ----------
    formset : `FormSet`
        A bound model formset constructed with `formset_factory` or similar.
    model_class : `any`
        The model that each form in the formset constructs.
    prefix : `str`, optional.
        The prefix of the formset if any.

    Returns
    -------
    `list`
        A list of instantiated models, but non-commited.
    """
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
                    if model.text not in set([o.text for o in objects]):
                        objects.append(model)
            else:
                objects.append(None)
    return objects


def parse_mapping_formset(reference_mapping_formset):
    """
    Parses a `ReferenceMappingFormSet` into a list of non-commited
    `ReferenceMapping` models. If the form is not valid for a particular
    form, then `None` is appended to the list.

    Parameters
    ----------
    reference_mapping_formset : `ReferenceMappingFormSet`
        A bound ReferenceMappingFormSet instance.

    Returns
    -------
    `list`
        A list of instantiated models, but non-commited.
    """
    objects = []
    for i, form in enumerate(reference_mapping_formset):
        if form.is_valid():
            if form.cleaned_data:
                model = form.save(commit=False)
                objects.append(model)
        else:
            objects.append(None)
    return objects


@login_required(login_url=reverse_lazy("accounts:login"))
def experiment_create_view(request):
    """
    This view serves up four types of forms:
        - `ExperimentForm` for the instantiation of an Experiment instnace.
        - `KeywordFormSet` for the instantiation and linking of M2M `Keyword`
           instnaces.
        - `ExternalAccessionFormSet` for the instantiation and linking of M2M
          `ExternalAccession` instnaces.
        - `ReferenceMappingFormSet` for the instantiation and linking of M2M
          `ReferenceMapping` instnaces.

    A new experiment instance will only be created if all forms pass validation
    otherwise the forms with the appropriate errors will be served back. Upon
    success, the user is redirected to the newly created experiment page.

    Parameters
    ----------
    request : `object`
        The request object that django passes into all views.
    """
    context = {}
    experiment_form = ExperimentForm(prefix=EXPERIMENT_FORM_PREFIX)
    keyword_formset = KeywordFormSet(prefix=KEYWORD_FORM_PREFIX)
    external_accession_formset = ExternalAccessionFormSet(
        prefix=EXTERNAL_ACCESSION_FORM_PREFIX
    )
    ref_mapping_formset = ReferenceMappingFormSet(
        prefix=REFERENCE_MAPPING_FORM_PREFIX
    )
    context["experiment_form"] = experiment_form
    context["keyword_formset"] = keyword_formset
    context["external_accession_formset"] = external_accession_formset
    context["reference_mapping_formset"] = ref_mapping_formset

    # If you change the prefix arguments here, make sure to change them
    # in the corresponding template element id fields as well. If you don't,
    # expect everything to break horribly. You've been warned.
    if request.method == "POST":
        experiment_form = ExperimentForm(
            request.POST, prefix=EXPERIMENT_FORM_PREFIX
        )
        keyword_formset = KeywordFormSet(
            request.POST, prefix=KEYWORD_FORM_PREFIX
        )
        external_accession_formset = ExternalAccessionFormSet(
            request.POST, prefix=EXTERNAL_ACCESSION_FORM_PREFIX
        )
        ref_mapping_formset = ReferenceMappingFormSet(
            request.POST, prefix=REFERENCE_MAPPING_FORM_PREFIX
        )
        context["experiment_form"] = experiment_form
        context["keyword_formset"] = keyword_formset
        context["external_accession_formset"] = external_accession_formset
        context["reference_mapping_formset"] = ref_mapping_formset

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

        # Save and update permissions. If no experimentset was selected, by
        # default a new experimentset is created with the current user as
        # its administrator.
        experiment.save()
        user = request.user
        assign_user_as_instance_admin(user, experiment)
        if not request.POST['{}-experimentset'.format(EXPERIMENT_FORM_PREFIX)]:
            assign_user_as_instance_admin(user, experiment.experimentset)

        accession = experiment.accession
        return redirect("experiment:experiment_detail", accession=accession)

    else:
        return render(
            request,
            "experiment/new_experiment.html",
            context=context
        )
