import json

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404
from django.http import StreamingHttpResponse
from django.views.generic import DetailView
from django.forms import formset_factory
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse_lazy
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from accounts.permissions import (
    assign_user_as_instance_admin,
    PermissionTypes
)

from experiment.models import Experiment

from main.models import (
    Keyword, ExternalAccession,
    TargetOrganism, ReferenceMapping
)
from main.forms import (
    KeywordForm, ExternalAccessionForm,
    ReferenceMappingForm, TargetOrganismForm
)

from .models import ScoreSet, Variant, SCORES_KEY, COUNTS_KEY
from .forms import ScoreSetForm


SCORESET_FORM_PREFIX = "scoreset"
KEYWORD_FORM_PREFIX = "keyword"
KeywordFormSet = formset_factory(KeywordForm)


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
        accession = self.kwargs.get('accession', None)
        return get_object_or_404(ScoreSet, accession=accession)

    def get_context_data(self, **kwargs):
        context = super(ScoreSetDetailView, self).get_context_data(**kwargs)
        instance = self.get_object()
        variant_list = instance.variant_set.all()
        paginator = Paginator(variant_list, 100)

        try:
            page = self.request.GET.get('page', 1)
            variants = paginator.page(page)
        except PageNotAnInteger:
            variants = paginator.page(1)
        except EmptyPage:
            variants = paginator.page(paginator.num_pages)

        context["variants"] = variants
        context["scores_columns"] = \
            context['scoreset'].dataset_columns[SCORES_KEY]
        context["counts_columns"] = \
            context['scoreset'].dataset_columns[COUNTS_KEY]

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
        The `ScoreSet` accession which will be queried.
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
        PermissionTypes.CAN_VIEW, scoreset)
    if scoreset.private and not has_permission:
        response = render(
            request=request,
            template_name="main/403_forbidden.html",
            context={"instance": scoreset},
        )
        response.status_code = 403
        return response

    variants = scoreset.variant_set.all()
    columns = scoreset.dataset_columns[dataset_key]

    def gen_repsonse():
        yield ','.join(columns) + '\n'
        for var in variants:
            data = []
            for column_key in columns:
                data.append(str(var.data[dataset_key][column_key]))
            yield ','.join(data) + '\n'

    return StreamingHttpResponse(gen_repsonse(), content_type='text')


def download_scoreset_metadata(request, accession):
    """
    This view returns the scoreset metadata in text format for viewing.

    Parameters
    ----------
    accession : `str`
        The `ScoreSet` accession which will be queried.

    Returns
    -------
    `StreamingHttpResponse`
        A stream is returned to handle the case where the data is too large
        to send all at once.
    """
    scoreset = get_object_or_404(ScoreSet, accession=accession)

    has_permission = request.user.has_perm(
        PermissionTypes.CAN_VIEW, scoreset)
    if scoreset.private and not has_permission:
        response = render(
            request=request,
            template_name="main/403_forbidden.html",
            context={"instance": scoreset},
        )
        response.status_code = 403
        return response

    json_response = json.dumps(scoreset.metadata)
    return HttpResponse(json_response, content_type="application/json")


@login_required(login_url=reverse_lazy("accounts:login"))
def scoreset_create_view(request):
    """
    A view to create a new scoreset. Upon successs, this view will redirect
    to the newly created scoreset object.

    If you change the prefix arguments here, make sure to change them
    in the corresponding template element id fields as well. If you don't,
    expect everything to break horribly.
    """
    context = {}
    scoreset_form = ScoreSetForm(prefix=SCORESET_FORM_PREFIX)
    context["scoreset_form"] = scoreset_form

    if request.method == "POST":
        scoreset_form = ScoreSetForm(
            request.POST, prefix=SCORESET_FORM_PREFIX)
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
        scoreset.save()
        user = request.user
        scoreset.created_by = user
        scoreset.last_edit_by = user
        scoreset.save()

        assign_user_as_instance_admin(user, scoreset)
        accession = scoreset.accession
        return redirect("scoreset:scoreset_detail", accession=accession)

    else:
        return render(
            request,
            "scoreset/new_scoreset.html",
            context=context
        )
