import json

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, StreamingHttpResponse
from django.http import Http404
from django.core.urlresolvers import reverse_lazy
from django.views.generic import DetailView
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from accounts.forms import send_admin_email
from accounts.permissions import assign_user_as_instance_admin, PermissionTypes

from main.utils.pandoc import convert_md_to_html
from main.utils.versioning import save_and_create_revision_if_tracked_changed

import dataset.constants as constants

from .models import Experiment, ExperimentSet, ScoreSet
from .forms import ExperimentForm, ExperimentEditForm
from .forms import ScoreSetForm, ScoreSetEditForm


class ExperimentDetailView(DetailView):
    """
    object in question and render a simple template for public viewing, or
    Simple class-based detail view for an `Experiment`. Will either find the
    404.

    Parameters
    ----------
    urn : `str`
        The urn of the `Experiment` to render.
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
        accession = self.kwargs.get('urn', None)
        return get_object_or_404(Experiment, accession=accession)


class ExperimentSetDetailView(DetailView):
    """
    Simple class-based detail view for an `ExperimentSet`. Will either find the
    object in question and render a simple template for public viewing, or
    404.

    Parameters
    ----------
    urn : `str`
        The urn of the `ExperimentSet` to render.
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
        accession = self.kwargs.get('urn', None)
        return get_object_or_404(ExperimentSet, accession=accession)


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
                if model.datahash not in set(m.datahash for m in objects):
                    objects.append(model)
        else:
            objects.append(None)
    return objects


@login_required(login_url=reverse_lazy("accounts:login"))
def experiment_create_view(request):
    """
    This view serves up four types of forms:
        - `ExperimentForm` for the instantiation of an Experiment instnace.
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
    pks = [i.pk for i in request.user.profile.administrator_experimentsets()]
    experimentsets = ExperimentSet.objects.filter(
        pk__in=set(pks)
    ).order_by("urn")

    experiment_form = ExperimentForm()
    experiment_form.fields["experimentset"].queryset = experimentsets
    context["experiment_form"] = experiment_form

    # If you change the prefix arguments here, make sure to change them
    # in base.js as well for the +/- buttons to work correctly.
    if request.method == "POST":
        # Get the new keywords/urn/target org so that we can return
        # them for list repopulation if the form has errors.
        keywords = request.POST.getlist("keywords")
        keywords = [kw for kw in keywords]
        e_accessions = request.POST.getlist("external_accessions")
        e_accessions = [ea for ea in e_accessions]
        target_organism = request.POST.getlist("target_organism")
        target_organism = [to for to in target_organism]

        experiment_form = ExperimentForm(request.POST)
        experiment_form.fields["experimentset"].queryset = experimentsets
        context["experiment_form"] = experiment_form
        context["repop_keywords"] = ','.join(keywords)
        context["repop_external_accessions"] = ','.join(e_accessions)
        context["repop_target_organism"] = ','.join(target_organism)

        if not experiment_form.is_valid():
            return render(
                request,
                "experiment/new_experiment.html",
                context=context
            )
        experiment = experiment_form.save(commit=True)

        # Save and update permissions. If no experimentset was selected,
        # by default a new experimentset is created with the current user
        # as it's administrator.
        user = request.user
        assign_user_as_instance_admin(user, experiment)
        experiment.created_by = user
        experiment.update_last_edit_info(user)
        save_and_create_revision_if_tracked_changed(user, experiment)

        if not request.POST['experimentset']:
            assign_user_as_instance_admin(user, experiment.experimentset)
            experiment.experimentset.created_by = user
            experiment.experimentset.update_last_edit_info(user)
            save_and_create_revision_if_tracked_changed(
                user, experiment.experimentset
            )

        return scoreset_create_view(
            request,
            came_from_new_experiment=True,
            e_accession=experiment.accession
        )
    else:
        return render(
            request,
            "experiment/new_experiment.html",
            context=context
        )


# --------------------------------------------------------------------------- #
#                               ScoreSet Views
# --------------------------------------------------------------------------- #
class ScoreSetDetailView(DetailView):
    """
    Simple detail view. See `scoreset/scoreset.html` for the template
    layout.
    """
    model = ScoreSet
    template_name = 'scoreset/scoreset.html'
    context_object_name = "scoreset"

    def dispatch(self, request, *args, **kwargs):
        try:
            scoreset = self.get_object()
        except Http404:
            response = render(
                request=request,
                template_name="main/404_not_found.html"
            )
            response.status_code = 404
            return response

        has_permission = self.request.user.has_perm(
            PermissionTypes.CAN_VIEW, scoreset)
        if scoreset.private and not has_permission:
            response = render(
                request=request,
                template_name="main/403_forbidden.html",
                context={"instance": scoreset},
            )
            response.status_code = 403
            return response
        else:
            return super(ScoreSetDetailView, self).dispatch(
                request, *args, **kwargs
            )

    def get_object(self):
        accession = self.kwargs.get('urn', None)
        return get_object_or_404(ScoreSet, accession=accession)

    def get_context_data(self, **kwargs):
        context = super(ScoreSetDetailView, self).get_context_data(**kwargs)
        instance = self.get_object()
        scores_variant_list = instance.variant_set.all().order_by("hgvs")

        if instance.has_counts_dataset():
            counts_variant_list = instance.variant_set.all().order_by("hgvs")
        else:
            counts_variant_list = instance.variant_set.none()

        try:
            counts_per_page = self.request.GET.get('counts-per-page', '')
            counts_per_page = int(counts_per_page)
        except:
            counts_per_page = 20

        try:
            scores_per_page = self.request.GET.get('scores-per-page', '')
            scores_per_page = int(scores_per_page)
        except:
            scores_per_page = 20

        scores_paginator = Paginator(
            scores_variant_list, per_page=scores_per_page)
        counts_paginator = Paginator(
            counts_variant_list, per_page=counts_per_page)

        try:
            scores_page = self.request.GET.get('scores-page', None)
            scores_variants = scores_paginator.page(scores_page)
        except PageNotAnInteger:
            scores_page = 1
            scores_variants = scores_paginator.page(scores_page)
        except EmptyPage:
            scores_page = scores_paginator.num_pages
            scores_variants = scores_paginator.page(scores_page)

        try:
            counts_page = self.request.GET.get('counts-page', None)
            counts_variants = counts_paginator.page(counts_page)
        except PageNotAnInteger:
            counts_page = 1
            counts_variants = counts_paginator.page(counts_page)
        except EmptyPage:
            counts_page = counts_paginator.num_pages
            counts_variants = counts_paginator.page(counts_page)

        # Handle the case when there are too many pages for scores.
        index = scores_paginator.page_range.index(scores_variants.number)
        max_index = len(scores_paginator.page_range)
        start_index = index - 5 if index >= 5 else 0
        end_index = index + 5 if index <= max_index - 5 else max_index
        page_range = scores_paginator.page_range[start_index:end_index]
        context["scores_page_range"] = page_range
        context["scores_variants"] = scores_variants
        context["scores_columns"] = \
            context['scoreset'].dataset_columns[constants.SCORES_KEY]

        # Handle the case when there are too many pages for counts.
        index = counts_paginator.page_range.index(counts_variants.number)
        max_index = len(counts_paginator.page_range)
        start_index = index - 5 if index >= 5 else 0
        end_index = index + 5 if index <= max_index - 5 else max_index
        page_range = counts_paginator.page_range[start_index:end_index]
        context["counts_page_range"] = page_range
        context["counts_variants"] = counts_variants
        context["counts_columns"] = \
            context['scoreset'].dataset_columns[constants.COUNTS_KEY]

        context["scores_per_page"] = scores_per_page
        context["counts_per_page"] = counts_per_page
        context["per_page_selections"] = [20, 50, 100]

        return context


def download_scoreset_data(request, accession, dataset_key):
    """
    This view returns the variant dataset in csv format for a specific
    `ScoreSet`. This will either be the 'scores' or 'counts' dataset, which
    are the only two supported keys in a scoreset's `dataset_columns`
    attributes.

    Parameters
    ----------
    accession : `str`
        The `ScoreSet` urn which will be queried.
    dataset_key : `str`
        The type of dataset requested. Currently this is either 'scores' or
        'counts' as these are the only two supported datasets.

    Returns
    -------
    `StreamingHttpResponse`
        A stream is returned to handle the case where the data is too large
        to send all at once.
    """
    scoreset = get_object_or_404(ScoreSet, accession=accession)

    has_permission = request.user.has_perm(
        PermissionTypes.CAN_VIEW, scoreset
    )
    if scoreset.private and not has_permission:
        response = render(
            request=request,
            template_name="main/403_forbidden.html",
            context={"instance": scoreset},
        )
        response.status_code = 403
        return response

    if not scoreset.has_counts_dataset() and dataset_key == constants.COUNTS_KEY:
        return StreamingHttpResponse("", content_type='text')

    variants = scoreset.variant_set.all().order_by("urn")
    columns = scoreset.dataset_columns[dataset_key]

    def gen_repsonse():
        yield ','.join(columns) + '\n'
        for var in variants:
            data = []
            for column_key in columns:
                data.append(str(var.data[dataset_key][column_key]))
            yield ','.join(data) + '\n'

    return StreamingHttpResponse(gen_repsonse(), content_type='text')


@login_required(login_url=reverse_lazy("accounts:login"))
def scoreset_create_view(request, came_from_new_experiment=False, e_accession=None):
    """
    A view to create a new scoreset. Upon successs, this view will redirect
    to the newly created scoreset object.

    If you change the prefix arguments here, make sure to change them
    in the corresponding template element id fields as well. If you don't,
    expect everything to break horribly.
    """
    context = {}
    scoreset_form = ScoreSetForm()

    pks = [i.pk for i in request.user.profile.administrator_experiments()]
    experiments = Experiment.objects.filter(
        pk__in=set(pks)
    ).order_by("urn")
    scoreset_form.fields["experiment"].queryset = experiments

    pks = [i.pk for i in request.user.profile.administrator_scoresets()]
    scoresets = ScoreSet.objects.filter(pk__in=set(pks)).order_by("urn")
    scoreset_form.fields["replaces"].queryset = scoresets

    if came_from_new_experiment:
        experiments = Experiment.objects.filter(accession=e_accession)
        scoreset_form.fields["experiment"].queryset = experiments
        context["scoreset_form"] = scoreset_form
        context["came_from_new_experiment"] = came_from_new_experiment
        context["e_accession"] = e_accession
        return render(
            request,
            "scoreset/new_scoreset.html",
            context=context
        )

    # If the request is ajax, then it's for previewing the abstract
    # or method description
    if request.is_ajax():
        data = {}
        data['abstract'] = convert_md_to_html(
            request.GET.get("abstract", "")
        )
        data['method_desc'] = convert_md_to_html(
            request.GET.get("method_desc", "")
        )
        return HttpResponse(json.dumps(data), content_type="application/json")

    if request.method == "POST":
        # Get the new keywords so that we can return them for
        # list repopulation if the form has errors.
        keywords = request.POST.getlist("keywords")
        keywords = [kw for kw in keywords]

        scoreset_form = ScoreSetForm(data=request.POST, files=request.FILES)
        scoreset_form.fields["experiment"].queryset = experiments
        scoreset_form.fields["replaces"].queryset = scoresets
        context["repop_keywords"] = ','.join(keywords)
        context["scoreset_form"] = scoreset_form

        if scoreset_form.is_valid():
            scoreset = scoreset_form.save(commit=True)
        else:
            return render(
                request,
                "scoreset/new_scoreset.html",
                context=context
            )

        # Save and update permissions. A user will not be added as an
        # admin to the parent experiment. This must be done by the admin
        # of said experiment.
        if request.POST.get("publish", None):
            scoreset.publish()
            send_admin_email(request.user, scoreset)

        user = request.user
        scoreset.created_by = user
        scoreset.last_edit_by = user
        scoreset.update_last_edit_info(user)
        save_and_create_revision_if_tracked_changed(user, scoreset)

        assign_user_as_instance_admin(user, scoreset)
        accession = scoreset.accession
        return redirect("scoreset:scoreset_detail", accession=accession)

    else:
        context["scoreset_form"] = scoreset_form
        return render(
            request,
            "scoreset/new_scoreset.html",
            context=context
        )
