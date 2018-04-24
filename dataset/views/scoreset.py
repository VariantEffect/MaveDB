import json
from braces.views import AjaxResponseMixin, LoginRequiredMixin, PermissionRequiredMixin

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.core.urlresolvers import reverse, reverse_lazy
from django.views.generic import DetailView, CreateView, TemplateView
from django.db import transaction

from accounts.forms import send_admin_email
from accounts.permissions import PermissionTypes, assign_user_as_instance_admin

from core.utilities import is_null
from core.utilities.pandoc import convert_md_to_html
from core.utilities.versioning import (
    track_changes
)

from genome.serializers import TargetGeneSerializer
from genome.models import TargetGene
from genome.forms import (
    ReferenceMapForm, TargetGeneForm,
    create_genomic_interval_formset
)

from ..models.scoreset import ScoreSet
from ..models.experiment import Experiment
from ..forms.scoreset import ScoreSetForm


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
        variants = instance.children.all().order_by("hgvs")[:20]
        context["variants"] = variants
        context["score_columns"] = instance.score_columns
        context["count_columns"] = instance.count_columns
        context["metadata_columns"] = instance.metadata_columns
        return context


@login_required(login_url=reverse_lazy("accounts:login"))
def scoreset_create_view(request, experiment_urn=None):
    """
    A view to create a new scoreset. Upon successs, this view will redirect
    to the newly created scoreset object.

    If you change the prefix arguments here, make sure to change them
    in the corresponding template element id fields as well. If you don't,
    expect everything to break horribly.
    """
    from metadata.forms import UniprotOffsetForm
    context = {}
    scoreset_form = ScoreSetForm(user=request.user)
    target_form = TargetGeneForm(user=request.user)
    reference_map_form = ReferenceMapForm()
    interval_form = GenomicIntervalForm()
    uniprot_form = UniprotOffsetForm()

    context["scoreset_form"] = scoreset_form
    context["target_form"] = target_form
    context["reference_map_form"] = reference_map_form
    context["interval_form"] = interval_form
    context["uniprot_form"] = uniprot_form

    if experiment_urn:
        experiments = Experiment.objects.filter(urn=experiment_urn)
        scoreset_form.fields["experiment"].queryset = experiments
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
        markdown = request.GET.get("markdown", False)
        if not markdown:
            target_id = request.GET.get("targetId", "")
            try:
                targetgene = TargetGene.objects.get(pk=target_id)
                reference_map = targetgene.get_reference_maps().first()
                genome = reference_map.get_reference_genome()
                interval = reference_map.get_intervals().first()
                data = {
                    'targetName': targetgene.get_name(),
                    'wildTypeSequence': targetgene.get_wt_sequence_string(),
                    'referenceGenome': genome.id,
                    'isPrimary': reference_map.is_primary_reference_map(),
                    'intervalStart': interval.get_start(),
                    'intervalEnd': interval.get_end(),
                    'chromosome': interval.get_chromosome(),
                    'strand': interval.get_strand()
                }
            except (AttributeError, ValueError) as e:
                data = {}
        else:
            data = {
                "abstractText": convert_md_to_html(
                    request.GET.get("abstractText", "")),
                "methodText": convert_md_to_html(
                    request.GET.get("methodText", ""))
            }

        return HttpResponse(
            json.dumps(data), content_type="application/json")

    if request.method == "POST":
        # Get the new keywords/urn/target org so that we can return
        # them for list repopulation if the form has errors.
        keywords = request.POST.getlist("keywords")
        keywords = [kw for kw in keywords if not is_null(kw)]

        sra_ids = request.POST.getlist("sra_ids")
        sra_ids = [i for i in sra_ids if not is_null(sra_ids)]

        doi_ids = request.POST.getlist("doi_ids")
        doi_ids = [i for i in doi_ids if not is_null(doi_ids)]

        pubmed_ids = request.POST.getlist("pubmed_ids")
        pubmed_ids = [i for i in pubmed_ids if not is_null(pubmed_ids)]

        # Setup the forms with the POST data. Keys for other forms
        # within POST should be ignored by the forms that don't use them.
        scoreset_form = ScoreSetForm(
            user=request.user,
            data=request.POST,
            files=request.FILES
        )
        target_form = TargetGeneForm(user=request.user, data=request.POST)
        reference_map_form = ReferenceMapForm(data=request.POST)
        # interval_form = GenomicIntervalForm(data=request.POST)

        context["repop_keywords"] = ','.join(keywords)
        context["repop_sra_identifiers"] = ','.join(sra_ids)
        context["repop_doi_identifiers"] = ','.join(doi_ids)
        context["repop_pubmed_identifiers"] = ','.join(pubmed_ids)

        context["scoreset_form"] = scoreset_form
        context["target_form"] = target_form
        context["reference_map_form"] = reference_map_form
        context["interval_form"] = interval_form

        all_valid = all([
            scoreset_form.is_valid(),
            target_form.is_valid(),
            reference_map_form.is_valid(),
            interval_form.is_valid()
        ])

        if not all_valid:
            return render(
                request,
                "dataset/scoreset/new_scoreset.html",
                context=context
            )
        else:
            user = request.user
            with transaction.atomic():
                scoreset = scoreset_form.save(commit=True)

                target_form.instance.scoreset = scoreset
                targetgene = target_form.save(commit=True)

                reference_map_form.instance.target = targetgene
                reference_map = reference_map_form.save(commit=True)

                interval_form.instance.reference_map = reference_map
                interval_form.save(commit=True)

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
                track_changes(user, scoreset)
                return redirect("dataset:scoreset_detail", urn=scoreset.urn)
    else:
        context["scoreset_form"] = scoreset_form
        return render(
            request,
            "dataset/scoreset/new_scoreset.html",
            context=context
        )


from formtools.wizard.views import WizardView
from django.views.generic import FormView


GenomicIntervalFormSet = create_genomic_interval_formset(
    extra=2, min_num=1, can_delete=False
)


class ScoreSetCreateView(FormView, AjaxResponseMixin, LoginRequiredMixin):
    form_class = ScoreSetForm
    template_name = 'dataset/scoreset/new_scoreset.html'
    login_url = '/login/'
    prefix = ''

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            return self.get_ajax(request)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        print(request.POST)

    def get_ajax(self, request, *args, **kwargs):
        # If the request is ajax, then it's for previewing the abstract
        # or method description. This code is coupled with base.js. Changes
        # here might break the javascript code.
        data = {
            "abstractText": convert_md_to_html(
                request.GET.get("abstractText", "")),
            "methodText": convert_md_to_html(
                request.GET.get("methodText", ""))
        }
        return HttpResponse(json.dumps(data), content_type="application/json")

    def get_success_url(self):
        scoreset_form = self.get_form(self.form_class)
        scoreset = scoreset_form.save(commit=True)
        return redirect('dataset:scoreset_detail', urn=scoreset.urn)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'form' in context:
            context['scoreset_form'] = context.pop('form')

        if self.request.method == "POST":
            # Get the new keywords/urn/target org so that we can return
            # them for list repopulation if the form has errors.
            keywords = self.request.POST.getlist("keywords")
            keywords = [kw for kw in keywords if not is_null(kw)]

            sra_ids = self.request.POST.getlist("sra_ids")
            sra_ids = [i for i in sra_ids if not is_null(sra_ids)]

            doi_ids = self.request.POST.getlist("doi_ids")
            doi_ids = [i for i in doi_ids if not is_null(doi_ids)]

            pubmed_ids = self.request.POST.getlist("pubmed_ids")
            pubmed_ids = [i for i in pubmed_ids if not is_null(pubmed_ids)]

            context["repop_keywords"] = ','.join(keywords)
            context["repop_sra_identifiers"] = ','.join(sra_ids)
            context["repop_doi_identifiers"] = ','.join(doi_ids)
            context["repop_pubmed_identifiers"] = ','.join(pubmed_ids)

        return context
