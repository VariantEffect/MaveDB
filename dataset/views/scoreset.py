import json

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import Http404, StreamingHttpResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import DetailView

from accounts.forms import send_admin_email
from accounts.permissions import PermissionTypes, assign_user_as_instance_admin

from main.utils import is_null
from main.utils.pandoc import convert_md_to_html
from main.utils.versioning import save_and_create_revision_if_tracked_changed

from dataset import constants as constants
from ..models.scoreset import ScoreSet
from ..models.experiment import Experiment
from ..forms.scoreset import ScoreSetForm


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

    def get_object(self, queryset=None):
        urn = self.kwargs.get('urn', None)
        return get_object_or_404(ScoreSet, urn=urn)

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
            context['scoreset'].dataset_columns[constants.score_columns]

        # Handle the case when there are too many pages for counts.
        index = counts_paginator.page_range.index(counts_variants.number)
        max_index = len(counts_paginator.page_range)
        start_index = index - 5 if index >= 5 else 0
        end_index = index + 5 if index <= max_index - 5 else max_index
        page_range = counts_paginator.page_range[start_index:end_index]
        context["counts_page_range"] = page_range
        context["counts_variants"] = counts_variants
        context["counts_columns"] = \
            context['scoreset'].dataset_columns[constants.count_columns]

        context["scores_per_page"] = scores_per_page
        context["counts_per_page"] = counts_per_page
        context["per_page_selections"] = [20, 50, 100]

        return context


def download_scoreset_data(request, urn, dataset_key):
    """
    This view returns the variant dataset in csv format for a specific
    `ScoreSet`. This will either be the 'scores' or 'counts' dataset, which
    are the only two supported keys in a scoreset's `dataset_columns`
    attributes.

    Parameters
    ----------
    urn : `str`
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
    scoreset = get_object_or_404(ScoreSet, urn=urn)

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

    if not scoreset.has_counts_dataset() and \
            dataset_key == constants.variant_count_data:
        return StreamingHttpResponse("", content_type='text')
    
    if not scoreset.has_metadata() and \
            dataset_key == constants.variant_metadata:
        return StreamingHttpResponse("", content_type='text')

    variants = scoreset.children.all().order_by("urn")
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
def scoreset_create_view(request, came_from_new_experiment=False,
                         experiment_urn=None):
    """
    A view to create a new scoreset. Upon successs, this view will redirect
    to the newly created scoreset object.

    If you change the prefix arguments here, make sure to change them
    in the corresponding template element id fields as well. If you don't,
    expect everything to break horribly.
    """
    context = {}
    scoreset_form = ScoreSetForm(user=request.user)

    if came_from_new_experiment:
        experiments = Experiment.objects.filter(urn=experiment_urn)
        scoreset_form.fields["experiment"].queryset = experiments
        context["scoreset_form"] = scoreset_form
        context["came_from_new_experiment"] = came_from_new_experiment
        context["experiment_urn"] = experiment_urn
        return render(
            request,
            "dataset/scoreset/new_scoreset.html",
            context=context
        )

    # If the request is ajax, then it's for previewing the abstract
    # or method description
    if request.is_ajax():
        data = dict()
        data['abstract_text'] = convert_md_to_html(
            request.GET.get("abstract_text", "")
        )
        data['method_text'] = convert_md_to_html(
            request.GET.get("method_text", "")
        )
        return HttpResponse(json.dumps(data), content_type="application/json")

    if request.method == "POST":
        # Get the new keywords/urn/target org so that we can return
        # them for list repopulation if the form has errors.
        keywords = request.POST.getlist("keywords")
        keywords = [kw for kw in keywords if not is_null(kw)]

        sra_ids = request.POST.getlist("sra_ids")
        sra_ids = [i for i in sra_ids if not is_null(sra_ids)]

        doi_ids = request.POST.getlist("doi_ids")
        doi_ids = [i for i in doi_ids if not is_null(doi_ids)]

        pubmed_ids = request.POST.getlist("pmid_ids")
        pubmed_ids = [i for i in pubmed_ids if not is_null(pubmed_ids)]

        target_organism = request.POST.getlist("target_organism")
        target_organism = [to for to in target_organism if not is_null(to)]

        scoreset_form = ScoreSetForm(data=request.POST, files=request.FILES)
        context["repop_keywords"] = ','.join(keywords)
        context["repop_sra_identifiers"] = ','.join(sra_ids)
        context["repop_doi_identifiers"] = ','.join(doi_ids)
        context["repop_pubmed_identifiers"] = ','.join(pubmed_ids)
        context["repop_target_organism"] = ','.join(target_organism)
        context["scoreset_form"] = scoreset_form

        if not scoreset_form.is_valid():
            return render(
                request,
                "dataset/scoreset/new_scoreset.html",
                context=context
            )
        else:
            scoreset = scoreset_form.save(commit=True)
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
            urn = scoreset.urn
            return redirect("dataset:scoreset_detail", urn=urn)

    else:
        context["scoreset_form"] = scoreset_form
        return render(
            request,
            "dataset/scoreset/new_scoreset.html",
            context=context
        )
