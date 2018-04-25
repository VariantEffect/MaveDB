import json
import logging
from braces.views import (
    AjaxResponseMixin, LoginRequiredMixin, PermissionRequiredMixin
)

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.core.urlresolvers import reverse_lazy
from django.views.generic import DetailView, FormView
from django.db import transaction

from accounts.forms import send_admin_email
from accounts.permissions import PermissionTypes, assign_user_as_instance_admin

from core.utilities import is_null
from core.utilities.pandoc import convert_md_to_html
from core.utilities.versioning import (
    track_changes
)

from metadata.forms import (
    UniprotOffsetForm,
    EnsemblOffsetForm,
    RefseqOffsetForm,
)

from genome.serializers import TargetGeneSerializer
from genome.models import TargetGene
from genome.forms import (
    ReferenceMapForm, TargetGeneForm,
    create_genomic_interval_formset,
    PimraryReferenceMapForm
)

from ..models.scoreset import ScoreSet
from ..models.experiment import Experiment
from ..forms.scoreset import ScoreSetForm


logger = logging.getLogger("django")
GenomicIntervaLFormSet = create_genomic_interval_formset(
    extra=0, min_num=1, can_delete=False
)


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


class ScoreSetCreateView(FormView, AjaxResponseMixin, LoginRequiredMixin):
    form_class = ScoreSetForm
    template_name = 'dataset/scoreset/new_scoreset.html'
    login_url = '/login/'
    success_url = '/accounts/profile/'
    prefix = ''

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            return self.get_ajax(request)

        context = self.get_context_data()
        if not context.get('has_permission', False):
            # Not really a success, but we need to get back to profile.
            urn = context.pop("experiment_urn")
            messages.error(
                self.request,
                "You do not have permission to access "
                "experiment {}. This action has reported to the local "
                "Police.".format(urn)
            )
            return HttpResponseRedirect(self.get_success_url())

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        scoreset_form = self.get_form()
        target_gene_form = self.get_target_gene_form()
        reference_map_form = self.get_reference_map_form()
        interval_formset = self.get_formset()
        uniprot_offset_form = self.get_uniprot_offset_form()
        refseq_offset_form = self.get_refseq_offset_form()
        ensembl_offset_form = self.get_ensembl_offset_form()
        forms = {
            "scoreset_form": scoreset_form,
            "target_gene_form": target_gene_form,
            "reference_map_form": reference_map_form,
            "interval_formset": interval_formset,
            "uniprot_offset_form": uniprot_offset_form,
            "refseq_offset_form": refseq_offset_form,
            "ensembl_offset_form": ensembl_offset_form,
        }
        all_valid = all([
            scoreset_form.is_valid(),
            target_gene_form.is_valid(),
            reference_map_form.is_valid(),
            interval_formset.is_valid(),
            uniprot_offset_form.is_valid(),
            ensembl_offset_form.is_valid(),
            refseq_offset_form.is_valid()
        ])

        if not all_valid:
            return self.form_invalid(forms)
        else:
            return self.form_valid(forms)

    def get_form_kwargs(self):
        # For scoreset form only.
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    # Form validation
    # --------------------------------------------------------------------- #
    def form_invalid(self, forms):
        """
        If the form is invalid, re-render the context data with the
        data-filled form and errors.
        """
        return self.render_to_response(self.get_context_data(**forms))

    def form_valid(self, forms):
        try:
            with transaction.atomic():
                scoreset_form = forms['scoreset_form']
                target_gene_form = forms['target_gene_form']
                reference_map_form = forms['reference_map_form']
                interval_formset = forms['interval_formset']
                uniprot_offset_form = forms['uniprot_offset_form']
                refseq_offset_form = forms['ensembl_offset_form']
                ensembl_offset_form = forms['refseq_offset_form']

                scoreset = scoreset_form.save(commit=True)

                target_gene_form.instance.scoreset = scoreset
                targetgene = target_gene_form.save(commit=True)

                reference_map_form.instance.target = targetgene
                reference_map = reference_map_form.save(commit=True)

                for form in interval_formset.forms:
                    form.instance.reference_map = reference_map
                    form.save(commit=True)

                uniprot_offset_form.save(target=targetgene, commit=True)
                refseq_offset_form.save(target=targetgene, commit=True)
                ensembl_offset_form.save(target=targetgene, commit=True)

                scoreset.set_created_by(self.request.user, propagate=False)
                scoreset.set_modified_by(self.request.user, propagate=False)
                scoreset.save(save_parents=False)
                assign_user_as_instance_admin(self.request.user, scoreset)
                track_changes(self.request.user, scoreset)

                messages.success(
                    self.request,
                    "Successfully created a new scoreset with the identifier "
                    "{}. You can freely edit this score set and add "
                    "additional reference maps from the edit view.".format(
                        scoreset.urn)
                )
                return HttpResponseRedirect(self.get_success_url())

        except Exception as e:
            logger.warning(
                "The following error occured during "
                "scoreset creation:\n{}".format(str(e))
            )
            messages.error(
                self.request,
                "There was a server side error while saving your submission "
                "Try again or contact us if this issue persists."
            )
            return self.form_invalid(forms)

    # Context
    # --------------------------------------------------------------------- #
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'form' in context:
            context['scoreset_form'] = context.pop('form')

        context["has_permission"] = True
        if self.request.GET.get("experiment", ""):
            urn = self.request.GET.get("experiment")
            experiment = get_object_or_404(Experiment, urn=urn)
            context["experiment_urn"] = urn
            has_permission = self.request.user.has_perm(
                PermissionTypes.CAN_VIEW, experiment)
            if has_permission:
                experiments = Experiment.objects.filter(urn=urn)
                if 'scoreset_form' in context:
                    scoreset_form = context.get('scoreset_form')
                    scoreset_form.fields[
                        'experiment'].queryset = experiments
                    context['scoreset_form'] = scoreset_form
                    context["has_permission"] = True
            else:
                context["has_permission"] = False

        if 'interval_formset' not in context:
            context['interval_formset'] = self.get_formset()
        if 'reference_map_form' not in context:
            context['reference_map_form'] = self.get_reference_map_form()
        if 'target_gene_form' not in context:
            context['target_gene_form'] = self.get_target_gene_form()
        if 'uniprot_offset_form' not in context:
            context['uniprot_offset_form'] = self.get_uniprot_offset_form()
        if 'ensembl_offset_form' not in context:
            context['ensembl_offset_form'] = self.get_ensembl_offset_form()
        if 'refseq_offset_form' not in context:
            context['refseq_offset_form'] = self.get_refseq_offset_form()

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

    # Ajax
    # ---------------------------------------------------------------------- #
    def get_ajax(self, request, *args, **kwargs):
        # If the request is ajax, then it's for previewing the abstract
        # or method description. This code is coupled with base.js. Changes
        # here might break the javascript code.
        data = {}
        if request.is_ajax():
            markdown = request.GET.get("markdown", False)
            target_id = request.GET.get("targetId", "")
            if target_id:
                if TargetGene.objects.filter(pk=target_id).count():
                    targetgene = TargetGene.objects.get(pk=target_id)
                    data = TargetGeneSerializer(targetgene).data
            elif markdown:
                data = {
                    "abstractText": convert_md_to_html(
                        request.GET.get("abstractText", "")),
                    "methodText": convert_md_to_html(
                        request.GET.get("methodText", ""))
                }
        return HttpResponse(json.dumps(data), content_type="application/json")

    # Extra forms
    # ---------------------------------------------------------------------- #
    def _make_form(self, form_class, instance=None,
                   queryset=None, user=None, initial=None, **kwargs):
        args = {}
        if instance:
            args["instance"] = instance
        if queryset:
            args["queryset"] = queryset
        if user:
            args["user"] = user
        if initial:
            args['initial'] = initial

        kwargs.update(args)
        if self.request.method == 'POST':
            return form_class(data=self.request.POST, **kwargs)
        else:
            return form_class(**kwargs)

    def get_formset(self, **kwargs):
        return self._make_form(GenomicIntervaLFormSet, **kwargs)

    def get_reference_map_form(self, **kwargs):
        return self._make_form(PimraryReferenceMapForm, **kwargs)

    def get_target_gene_form(self, **kwargs):
        return self._make_form(
            TargetGeneForm, user=self.request.user, **kwargs)

    def get_uniprot_offset_form(self, **kwargs):
        if 'prefix' not in kwargs:
            kwargs['prefix'] = "uniprot-offset-form"
        return self._make_form(UniprotOffsetForm, **kwargs)

    def get_ensembl_offset_form(self, **kwargs):
        if 'prefix' not in kwargs:
            kwargs['prefix'] = "ensembl-offset-form"
        return self._make_form(EnsemblOffsetForm, **kwargs)

    def get_refseq_offset_form(self, **kwargs):
        if 'prefix' not in kwargs:
            kwargs['prefix'] = "refseq-offset-form"
        return self._make_form(RefseqOffsetForm, **kwargs)
