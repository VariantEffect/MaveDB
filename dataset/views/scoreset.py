import json
import logging
from braces.views import AjaxResponseMixin

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import (
    Http404, HttpResponse, HttpResponseRedirect
)
from django.shortcuts import render, get_object_or_404, reverse
from django.views.generic import DetailView, FormView, UpdateView
from django.db import transaction

from core.utilities import send_admin_email
from core.mixins import MultiFormMixin
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
    PimraryReferenceMapForm,
    ReferenceMapManagementForm,
    create_reference_map_interval_nested_formset
)

from ..models.scoreset import ScoreSet
from ..models.experiment import Experiment
from ..forms.scoreset import ScoreSetForm, ScoreSetEditForm

logger = logging.getLogger("django")
GenomicIntervaLFormSet = create_genomic_interval_formset(
    extra=0, min_num=1, can_delete=False
)
GenomicIntervaLFormSetWithDelete = create_genomic_interval_formset(
    extra=0, min_num=1, can_delete=True
)
NestedFormSet = create_reference_map_interval_nested_formset(
    outer_kwargs=dict(extra=0, min_num=1, can_delete=False),
    inner_kwargs=dict(extra=5, min_num=1, can_delete=False),
)
NestedFormSetWithDelete = create_reference_map_interval_nested_formset(
    outer_kwargs=dict(extra=0, min_num=1, can_delete=True),
    inner_kwargs=dict(extra=5, min_num=1, can_delete=True),
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


class ScoreSetCreateView(LoginRequiredMixin, FormView,
                         AjaxResponseMixin, MultiFormMixin):
    form_class = ScoreSetForm
    template_name = 'dataset/scoreset/new_scoreset.html'
    success_url = '/accounts/profile/'
    login_url = '/login/'
    prefix = ''

    def dispatch(self, request, *args, **kwargs):
        self.experiments = None
        if self.request.GET.get("experiment", ""):
            urn = self.request.GET.get("experiment")
            if Experiment.objects.filter(urn=urn).count():
                experiment = Experiment.objects.get(urn=urn)
                has_permission = self.request.user.has_perm(
                    PermissionTypes.CAN_VIEW, experiment)
                if has_permission:
                    self.experiments = \
                        Experiment.objects.filter(urn=urn)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            return self.get_ajax(request, *args, **kwargs)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        scoreset_form = self.get_form()
        target_gene_form = self.get_target_gene_form()
        reference_map_form = self.get_reference_map_form()
        uniprot_offset_form = self.get_uniprot_offset_form()
        refseq_offset_form = self.get_refseq_offset_form()
        ensembl_offset_form = self.get_ensembl_offset_form()
        forms = {
            "scoreset_form": scoreset_form,
            "target_gene_form": target_gene_form,
            "reference_map_form": reference_map_form,
            "uniprot_offset_form": uniprot_offset_form,
            "refseq_offset_form": refseq_offset_form,
            "ensembl_offset_form": ensembl_offset_form,
        }
        all_valid = all([
            scoreset_form.is_valid(),
            target_gene_form.is_valid(),
            reference_map_form.is_valid(),
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
                uniprot_offset_form = forms['uniprot_offset_form']
                refseq_offset_form = forms['ensembl_offset_form']
                ensembl_offset_form = forms['refseq_offset_form']

                scoreset = scoreset_form.save(commit=True)

                target_gene_form.instance.scoreset = scoreset
                targetgene = target_gene_form.save(commit=True)

                reference_map_form.instance.target = targetgene
                reference_map_form.save(commit=True)

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
    def update_context_with_additional_forms(self, context):
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
        return context

    def get_base_context(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method == "POST":
            # Get the new keywords/urn/target org so that we can return
            # them for list repopulation if the form has errors.
            keywords = self.request.POST.getlist("keywords")
            keywords = [kw for kw in keywords if not is_null(kw)]

            sra_ids = self.request.POST.getlist("sra_ids")
            sra_ids = [i for i in sra_ids if not is_null(i)]

            doi_ids = self.request.POST.getlist("doi_ids")
            doi_ids = [i for i in doi_ids if not is_null(i)]

            pubmed_ids = self.request.POST.getlist("pubmed_ids")
            pubmed_ids = [i for i in pubmed_ids if not is_null(i)]

            uniprot_id = self.request.POST.getlist("uniprot_id")
            uniprot_id = [i for i in uniprot_id if not is_null(i)]

            ensembl_id = self.request.POST.getlist("ensembl_ids")
            ensembl_id = [i for i in ensembl_id if not is_null(i)]

            refseq_id = self.request.POST.getlist("refseq_ids")
            refseq_id = [i for i in refseq_id if not is_null(i)]

            context["repop_keywords"] = ','.join(keywords)
            context["repop_sra_identifiers"] = ','.join(sra_ids)
            context["repop_doi_identifiers"] = ','.join(doi_ids)
            context["repop_pubmed_identifiers"] = ','.join(pubmed_ids)
            context["repop_uniprot_identifier"] = ','.join(uniprot_id)
            context["repop_ensembl_identifier"] = ','.join(ensembl_id)
            context["repop_refseq_identifier"] = ','.join(refseq_id)

        return context

    def get_context_data(self, **kwargs):
        context = self.get_base_context(**kwargs)
        if 'form' in context:
            context['scoreset_form'] = context.pop('form')
            if self.experiments is not None and self.experiments.count():
                context['scoreset_form'].fields['experiment'].queryset = \
                    self.experiments.all()
                context["experiment_urn"] = self.experiments.first().urn

        context = self.update_context_with_additional_forms(context)
        return context

    # Ajax
    # ---------------------------------------------------------------------- #
    def get_ajax(self, request, *args, **kwargs):
        # If the request is ajax, then it's for previewing the abstract
        # or method description. This code is coupled with base.js. Changes
        # here might break the javascript code.
        data = {}
        if 'targetId' in request.GET:
            pk = request.GET.get("targetId", "")
            if pk and TargetGene.objects.filter(pk=pk).count():
                targetgene = TargetGene.objects.get(pk=pk)
                data.update(TargetGeneSerializer(targetgene).data)
                map = targetgene.reference_maps.first()
                if map is not None:
                    data['genome'] = map.genome.pk
        if 'abstractText' in request.GET:
            data.update({
                "abstractText": convert_md_to_html(
                    request.GET.get("abstractText", "")),
            })
        if 'methodText' in request.GET:
            data.update({
                "methodText": convert_md_to_html(
                    request.GET.get("methodText", "")),
            })
        if 'experiment' in request.GET:
            pk = request.GET.get("experiment", "")
            if pk and Experiment.objects.filter(pk=pk).count():
                experiment = Experiment.objects.get(pk=pk)
                scoresets = [
                    (s.pk, s.urn) for s in experiment.scoresets.order_by('urn')
                    if self.request.user.has_perm(PermissionTypes.CAN_EDIT, s)
                ]
                data.update({'scoresets': scoresets})
                data.update(
                    {'keywords': [k.text for k in experiment.keywords.all()]}
                )

        return HttpResponse(json.dumps(data), content_type="application/json")

    # Extra forms
    # ---------------------------------------------------------------------- #
    def get_reference_map_form(self, **kwargs):
        return self._make_form(PimraryReferenceMapForm, **kwargs)

    def get_target_gene_form(self, **kwargs):
        return self._make_form(
            TargetGeneForm, user=self.request.user, **kwargs)

    def get_uniprot_offset_form(self, **kwargs):
        if 'prefix' not in kwargs:
            kwargs['prefix'] = "uniprot-offset"
        return self._make_form(UniprotOffsetForm, **kwargs)

    def get_ensembl_offset_form(self, **kwargs):
        if 'prefix' not in kwargs:
            kwargs['prefix'] = "ensembl-offset"
        return self._make_form(EnsemblOffsetForm, **kwargs)

    def get_refseq_offset_form(self, **kwargs):
        if 'prefix' not in kwargs:
            kwargs['prefix'] = "refseq-offset"
        return self._make_form(RefseqOffsetForm, **kwargs)



class ScoreSetEditView(PermissionRequiredMixin, FormView,
                         AjaxResponseMixin, MultiFormMixin):
    form_class = ScoreSetForm
    template_name = 'accounts/profile_edit.html'
    success_url = '/accounts/profile/'
    login_url = '/login/'
    prefix = ''
    permission_required = 'dataset.can_edit'
    redirect_unauthenticated_users = login_url
    raise_exception = True

    def has_permission(self):
        """
        Override this method to customize the way permissions are checked.
        """
        perms = self.get_permission_required()
        return self.request.user.has_perms(perms, self.scoreset)

    # Dispatch/Post/Get
    # ----------------------------------------------------------------------- #
    def dispatch(self, request, *args, **kwargs):
        try:
            urn = self.kwargs.get('urn', None)
            self.scoreset = get_object_or_404(ScoreSet, urn=urn)
        except PermissionDenied:
            urn = self.kwargs.get('urn', None)
            messages.error(
                self.request,
                "You do not have permission to edit {}. "
                "This action has reported to the local "
                "Police.".format(urn)
            )
            return HttpResponseRedirect(reverse("accounts:profile"))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            return self.get_ajax(request, *args, **kwargs)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        scoreset_form = self.get_form()
        target_gene_form = self.get_target_gene_form()
        reference_map_form = self.get_reference_map_form()
        uniprot_offset_form = self.get_uniprot_offset_form()
        refseq_offset_form = self.get_refseq_offset_form()
        ensembl_offset_form = self.get_ensembl_offset_form()
        forms = {
            "scoreset_form": scoreset_form,
            "target_gene_form": target_gene_form,
            "reference_map_form": reference_map_form,
            "uniprot_offset_form": uniprot_offset_form,
            "refseq_offset_form": refseq_offset_form,
            "ensembl_offset_form": ensembl_offset_form,
        }
        all_valid = all([
            scoreset_form.is_valid(),
            target_gene_form.is_valid(),
            reference_map_form.is_valid(),
            uniprot_offset_form.is_valid(),
            ensembl_offset_form.is_valid(),
            refseq_offset_form.is_valid()
        ])

        if not all_valid:
            return self.form_invalid(forms)
        else:
            return self.form_valid(forms)

    def get_form(self, form_class=None):
        if self.scoreset.private:
            return super().get_form()
        return super().get_form(form_class=ScoreSetEditForm)

    def get_form_kwargs(self):
        # For scoreset form only.
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['instance'] = self.scoreset
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
                scoreset = scoreset_form.save(commit=True)

                if self.scoreset.private:
                    target_gene_form = forms['target_gene_form']
                    reference_map_form = forms['reference_map_form']
                    uniprot_offset_form = forms['uniprot_offset_form']
                    refseq_offset_form = forms['ensembl_offset_form']
                    ensembl_offset_form = forms['refseq_offset_form']

                    target_gene_form.instance.scoreset = scoreset
                    targetgene = target_gene_form.save(commit=True)

                    reference_map_form.instance.target = targetgene
                    reference_map_form.save(commit=True)

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
    def update_context_with_additional_forms(self, context):
        if self.scoreset.private:
            targetgene = self.scoreset.get_target()
            if targetgene:
                ref_map = targetgene.get_reference_maps().first()
                uniprot_offset = targetgene.get_uniprot_offset_annotation()
                ensembl_offset = targetgene.get_ensembl_offset_annotation()
                refseq_offset = targetgene.get_refseq_offset_annotation()
            else:
                ref_map = None
                uniprot_offset = None
                ensembl_offset = None
                refseq_offset = None

            if 'reference_map_form' not in context:
                context['reference_map_form'] = \
                    self.get_reference_map_form(instance=ref_map)
            if 'target_gene_form' not in context:
                context['target_gene_form'] = \
                    self.get_target_gene_form(instance=targetgene)
            if 'uniprot_offset_form' not in context:
                context['uniprot_offset_form'] = \
                    self.get_uniprot_offset_form(instance=uniprot_offset)
            if 'ensembl_offset_form' not in context:
                context['ensembl_offset_form'] = \
                    self.get_ensembl_offset_form(instance=ensembl_offset)
            if 'refseq_offset_form' not in context:
                context['refseq_offset_form'] = \
                    self.get_refseq_offset_form(instance=refseq_offset)
            return context
        return context

    def get_base_context(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method == "POST":
            # Get the new keywords/urn/target org so that we can return
            # them for list repopulation if the form has errors.
            keywords = self.request.POST.getlist("keywords")
            keywords = [kw for kw in keywords if not is_null(kw)]

            sra_ids = self.request.POST.getlist("sra_ids")
            sra_ids = [i for i in sra_ids if not is_null(i)]

            doi_ids = self.request.POST.getlist("doi_ids")
            doi_ids = [i for i in doi_ids if not is_null(i)]

            pubmed_ids = self.request.POST.getlist("pubmed_ids")
            pubmed_ids = [i for i in pubmed_ids if not is_null(i)]

            uniprot_id = self.request.POST.getlist("uniprot_id")
            uniprot_id = [i for i in uniprot_id if not is_null(i)]

            ensembl_id = self.request.POST.getlist("ensembl_ids")
            ensembl_id = [i for i in ensembl_id if not is_null(i)]

            refseq_id = self.request.POST.getlist("refseq_ids")
            refseq_id = [i for i in refseq_id if not is_null(i)]

            context["repop_keywords"] = ','.join(keywords)
            context["repop_sra_identifiers"] = ','.join(sra_ids)
            context["repop_doi_identifiers"] = ','.join(doi_ids)
            context["repop_pubmed_identifiers"] = ','.join(pubmed_ids)
            context["repop_uniprot_identifier"] = ','.join(uniprot_id)
            context["repop_ensembl_identifier"] = ','.join(ensembl_id)
            context["repop_refseq_identifier"] = ','.join(refseq_id)

        return context

    ###
    def get_context_data(self, **kwargs):
        context = self.get_base_context(**kwargs)
        if 'form' in context:
            context['scoreset_form'] = context.pop('form')

        context = self.update_context_with_additional_forms(context)
        return context

    # Ajax
    # ---------------------------------------------------------------------- #
    def get_ajax(self, request, *args, **kwargs):
        # If the request is ajax, then it's for previewing the abstract
        # or method description. This code is coupled with base.js. Changes
        # here might break the javascript code.
        data = {}
        if 'targetId' in request.GET:
            pk = request.GET.get("targetId", "")
            if pk and TargetGene.objects.filter(pk=pk).count():
                targetgene = TargetGene.objects.get(pk=pk)
                data.update(TargetGeneSerializer(targetgene).data)
                map = targetgene.reference_maps.first()
                if map is not None:
                    data['genome'] = map.genome.pk
        if 'abstractText' in request.GET:
            data.update({
                "abstractText": convert_md_to_html(
                    request.GET.get("abstractText", "")),
            })
        if 'methodText' in request.GET:
            data.update({
                "methodText": convert_md_to_html(
                    request.GET.get("methodText", "")),
            })
        if 'experiment' in request.GET:
            pk = request.GET.get("experiment", "")
            if pk and Experiment.objects.filter(pk=pk).count():
                experiment = Experiment.objects.get(pk=pk)
                scoresets = [
                    (s.pk, s.urn) for s in experiment.scoresets.order_by('urn')
                    if self.request.user.has_perm(PermissionTypes.CAN_EDIT, s)
                ]
                data.update({'scoresets': scoresets})
                data.update(
                    {'keywords': [k.text for k in experiment.keywords.all()]}
                )

        return HttpResponse(json.dumps(data), content_type="application/json")

    # Extra forms
    # ---------------------------------------------------------------------- #
    def get_reference_map_form(self, **kwargs):
        return self._make_form(PimraryReferenceMapForm, **kwargs)

    def get_target_gene_form(self, **kwargs):
        return self._make_form(
            TargetGeneForm, user=self.request.user, **kwargs)

    def get_uniprot_offset_form(self, **kwargs):
        if 'prefix' not in kwargs:
            kwargs['prefix'] = "uniprot-offset"
        return self._make_form(UniprotOffsetForm, **kwargs)

    def get_ensembl_offset_form(self, **kwargs):
        if 'prefix' not in kwargs:
            kwargs['prefix'] = "ensembl-offset"
        return self._make_form(EnsemblOffsetForm, **kwargs)

    def get_refseq_offset_form(self, **kwargs):
        if 'prefix' not in kwargs:
            kwargs['prefix'] = "refseq-offset"
        return self._make_form(RefseqOffsetForm, **kwargs)


# --------------------------------------------------------------------------- #
#                  NOT TESTED/STILL REQUIRES DEVELOPMENT
# --------------------------------------------------------------------------- #
# class ReferenceMapEditView(PermissionRequiredMixin, FormView, AjaxResponseMixin,
#                            MultiFormMixin):
#     form_class = ReferenceMapForm
#     template_name = 'dataset/scoreset/edit_reference_maps.html'
#     login_url = '/login/'
#     success_url = '/accounts/profile/'
#     prefix = ''
#     permission_required = 'dataset.can_edit'
#     redirect_unauthenticated_users = login_url
#     raise_exception = True
#
#     def create_forms(self, request, *args, **kwargs):
#         map_ = None
#         if request.method == 'GET':
#             management_form = self.get_management_form(data=request.GET)
#         else:
#             management_form = self.get_management_form(data=request.POST)
#
#         if not management_form.is_valid():
#             return self.form_invalid(
#                 {'reference_management_form': management_form}
#             )
#
#         # The following code instatiates news forms based on a selected
#         # reference map instance when the user selects a reference map from
#         # the drop-down menu and sends a GET request for the pre-populated
#         # forms.
#         selected = management_form.get_selected_reference_map()
#         maps = self.scoreset.get_target().get_reference_maps()
#         if selected is None:
#             reference_map_form = self.get_reference_map_form()
#             interval_formset = self.get_formset()
#         else:
#             if not maps.filter(id=selected).count():
#                 messages.error(
#                     request,
#                     "Could not find an existing reference "
#                     "map for {}".format(selected.genome)
#                 )
#                 reference_map_form = self.get_reference_map_form()
#                 interval_formset = self.get_formset()
#             else:
#                 map_ = maps.get(id=selected)
#                 messages.debug(
#                     request,
#                     "DEBUG: You are editing map {}|{}".format(map_.pk, map_.genome)
#                 )
#                 reference_map_form = self.get_reference_map_form(instance=map_)
#                 interval_formset = self.get_formset(
#                     queryset=map_.get_intervals())
#
#         return {
#             'reference_map_form': reference_map_form,
#             'interval_formset': interval_formset,
#             'management_form': management_form,
#             'selected': map_
#         }
#
#     # Dispatch/Post/Get
#     # ----------------------------------------------------------------------- #
#     def dispatch(self, request, *args, **kwargs):
#         try:
#             self.scoreset = get_object_or_404(self.kwargs.get('urn', None))
#             return super().dispatch(request, *args, **kwargs)
#         except PermissionDenied:
#             urn = self.kwargs.get('urn', None)
#             messages.error(
#                 self.request,
#                 "You do not have permission to edit {}. "
#                 "This action has reported to the local "
#                 "Police.".format(urn)
#             )
#             return HttpResponseRedirect(reverse("accounts:profile"))
#
#     def get(self, request, *args, **kwargs):
#         if request.is_ajax():
#             return self.get_ajax(request, *args, **kwargs)
#         forms = self.create_forms(request)
#         return self.render_to_response(self.get_context_data(**forms))
#
#
#     def post(self, request, *args, **kwargs):
#         forms = self.create_forms(request)
#         for form in forms.values():
#             if not form.is_valid():
#                 return self.form_invalid(forms)
#         return self.form_valid(forms)
#
#     # Form validation
#     # ----------------------------------------------------------------------- #
#     def form_valid(self, forms):
#         management_form = forms.get("management_form")
#         reference_map_form = forms.get("reference_map_form")
#         interval_formset = forms.get("interval_formset")
#
#         selected_map = management_form.get_selected_reference_map()
#         if selected_map is None:
#             targetgene = self.scoreset.get_target()
#             reference_map_form.instance.target = targetgene
#             new_map = reference_map_form.save(commit=True)
#             intervals = interval_formset.save(
#                 reference_map=new_map, commit=True)
#         else:
#             existing_map = reference_map_form.save(commit=True)
#             intervals = interval_formset.save(
#                 reference_map=existing_map, commit=True)
#
#         return super().form_valid(forms)
#
#     def form_invalid(self, forms):
#         """
#         If the form is invalid, re-render the context data with the
#         data-filled form and errors.
#         """
#         return self.render_to_response(self.get_context_data(**forms))
#
#     # Context helpers
#     # ----------------------------------------------------------------------- #
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         if 'reference_map_form' not in context:
#             context['reference_map_form'] = self.get_reference_map_form()
#         if 'interval_formset' not in context:
#             context['interval_formset'] = self.get_formset()
#         if 'reference_management_form' not in context:
#             context["reference_management_form"] = \
#                 self.get_management_form(data=self.request.GET)
#         return context
#
#     # Get forms
#     # ----------------------------------------------------------------------- #
#     def get_formset(self, **kwargs):
#         return self._make_form(GenomicIntervaLFormSetWithDelete, **kwargs)
#
#     def get_reference_map_form(self, **kwargs):
#         return self._make_form(ReferenceMapForm, **kwargs)
#
#     def get_management_form(self, **kwargs):
#         return self._make_form(ReferenceMapManagementForm, **kwargs)
#
#     # GET ajax handler
#     # ----------------------------------------------------------------------- #
#     def get_ajax(self, request, *args, **kwargs):
#         data = {}
#         if 'targetId' in request.GET:
#             pk = request.GET.get("targetId", "")
#             if pk and TargetGene.objects.filter(pk=pk).count():
#                 targetgene = TargetGene.objects.get(pk=pk)
#                 data.update(TargetGeneSerializer(targetgene).data)
#         return HttpResponse(json.dumps(data), content_type="application/json")
