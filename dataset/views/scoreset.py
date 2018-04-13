import json
from braces.views import AjaxResponseMixin, LoginRequiredMixin
from nested_formset import nestedformset_factory

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.core.urlresolvers import reverse, reverse_lazy
from django.views.generic import DetailView, CreateView

from accounts.forms import send_admin_email
from accounts.permissions import PermissionTypes, assign_user_as_instance_admin

from core.views import MultipleFormsView
from core.utilities import is_null
from core.utilities.pandoc import convert_md_to_html
from core.utilities.versioning import (
    save_and_create_revision_if_tracked_changed
)

from genome.forms import NestedAnnotationFormSet

from dataset import constants as constants
from ..models.scoreset import ScoreSet
from ..models.experiment import Experiment
from ..forms.scoreset import ScoreSetForm


class ScoreSetCreateView(MultipleFormsView,
                         AjaxResponseMixin,
                         LoginRequiredMixin):
    """
    This view handles the rendering/submission/validation loop of two forms:
        - :class:`ScoreSetForm`
        - :class:`NestedAnnotationFormSet`

    The ScoreSet form defines the selection of a
    :class:`genome.models.TargetGene`, or the creation of a new one.
    For this target gene, at a series of annotations can be defined, each
    with their own series of intervals.
    """

    template_name = 'dataset/scoreset/scoreset_new.html'
    login_url = reverse_lazy('accounts:login')
    form_classes = {
        'scoreset': ScoreSetForm,
        'annotations': NestedAnnotationFormSet
    }

    def get_success_url(self, form_name=None):
        return reverse('dataset:scoreset_detail', args=(self.scoreset.urn,))

    def scoreset_form_valid(self, form):
        self.scoreset = form.save(commit=True)

    def get_ajax(self, request, *args, **kwargs):
        """User submits a GET request for previewing abstract/method."""
        pass

    def post_ajax(self, request, *args, **kwargs):
        """User submits a POST request when the target is changed."""
        pass


class ScoreSetDetailView(DetailView):
    """
    Simple detail view. See `scoreset/scoreset.html` for the template
    layout.
    """
    model = ScoreSet
    template_name = 'dataset/scoreset/scoreset.html'
    context_object_name = "instance"

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
        variants = instance.children.all().order_by("hgvs")[:10]
        context["variants"] = variants
        context["score_columns"] = \
            instance.dataset_columns[constants.score_columns]
        context["counts_columns"] = \
            instance.dataset_columns[constants.count_columns]
        context["metadata_columns"] = \
            instance.dataset_columns[constants.metadata_columns]
        return context


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
    # or method description. This code is coupled with base.js. Changes
    # here might break the javascript code.
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

        scoreset_form = ScoreSetForm(
            user=request.user, data=request.POST, files=request.FILES)
        context["repop_keywords"] = ','.join(keywords)
        context["repop_sra_identifiers"] = ','.join(sra_ids)
        context["repop_doi_identifiers"] = ','.join(doi_ids)
        context["repop_pubmed_identifiers"] = ','.join(pubmed_ids)
        context["scoreset_form"] = scoreset_form

        print("Validating...")
        if not scoreset_form.is_valid():
            print("Failed...")
            return render(
                request,
                "dataset/scoreset/new_scoreset.html",
                context=context
            )
        else:
            print("Saving...")
            user = request.user
            scoreset = scoreset_form.save(commit=True)
            scoreset.set_created_by(user, propagate=False)
            # Save and update permissions. A user will not be added as an
            # admin to the parent experiment. This must be done by the admin
            # of said experiment.
            if request.POST.get("publish", None):
                scoreset.publish(propagate=True)
                scoreset.set_modified_by(user, propagate=True)
                scoreset.save(save_parents=True)
                send_admin_email(request.user, scoreset)
            else:
                scoreset.set_modified_by(user, propagate=False)
                scoreset.save(save_parents=False)

            assign_user_as_instance_admin(user, scoreset)
            save_and_create_revision_if_tracked_changed(user, scoreset)
            return redirect("dataset:scoreset_detail", urn=scoreset.urn)
    else:
        context["scoreset_form"] = scoreset_form
        return render(
            request,
            "dataset/scoreset/new_scoreset.html",
            context=context
        )
