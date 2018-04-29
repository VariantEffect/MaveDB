import logging

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, reverse
from django.db import transaction

from accounts.permissions import (
    PermissionTypes, assign_user_as_instance_admin
)

from core.utilities import send_admin_email
from core.utilities.versioning import track_changes

from metadata.forms import (
    UniprotOffsetForm,
    EnsemblOffsetForm,
    RefseqOffsetForm,
)

from genome.forms import PimraryReferenceMapForm, TargetGeneForm

from ..models.scoreset import ScoreSet
from ..models.experiment import Experiment
from ..forms.scoreset import ScoreSetForm, ScoreSetEditForm
from ..mixins import ScoreSetAjaxMixin

from .base import (
    DatasetModelView, CreateDatasetModelView, UpdateDatasetModelView
)

logger = logging.getLogger("django")


class ScoreSetDetailView(DatasetModelView):
    """
    Simple detail view. See `scoreset/scoreset.html` for the template
    layout.
    """
    # Overriding from `DatasetModelView`.
    # -------
    model = ScoreSet
    template_name = 'dataset/scoreset/scoreset.html'
    # -------

    def get_context_data(self, **kwargs):
        context = super(ScoreSetDetailView, self).get_context_data(**kwargs)
        instance = self.get_object()
        variants = instance.children.all().order_by("hgvs")[:20]
        context["variants"] = variants
        context["score_columns"] = instance.score_columns
        context["count_columns"] = instance.count_columns
        context["metadata_columns"] = instance.metadata_columns
        return context


class ScoreSetCreateView(ScoreSetAjaxMixin, CreateDatasetModelView):
    # Overridden from `CreateDatasetModelView`
    # -------
    form_class = ScoreSetForm
    template_name = 'dataset/scoreset/new_scoreset.html'
    model_class_name = 'Score set'
    # -------

    prefixes = {
        'uniprot_offset_form': 'uniprot-offset',
        'refseq_offset_form': 'refseq-offset',
        'ensembl_offset_form': 'ensembl-offset',
    }
    forms = {
        "scoreset_form": ScoreSetForm,
        "target_gene_form": TargetGeneForm,
        "reference_map_form": PimraryReferenceMapForm,
        "uniprot_offset_form": UniprotOffsetForm,
        "refseq_offset_form": RefseqOffsetForm,
        "ensembl_offset_form": EnsemblOffsetForm,
    }

    def dispatch(self, request, *args, **kwargs):
        if self.request.GET.get("experiment", ""):
            urn = self.request.GET.get("experiment")
            if Experiment.objects.filter(urn=urn).count():
                experiment = Experiment.objects.get(urn=urn)
                has_permission = self.request.user.has_perm(
                    PermissionTypes.CAN_VIEW, experiment)
                if has_permission:
                    self.kwargs['experiment'] = experiment
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def save_forms(self, forms):
        scoreset_form = forms['scoreset_form']
        target_gene_form = forms['target_gene_form']
        reference_map_form = forms['reference_map_form']
        uniprot_offset_form = forms['uniprot_offset_form']
        refseq_offset_form = forms['refseq_offset_form']
        ensembl_offset_form = forms['ensembl_offset_form']

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
        self.kwargs['urn'] = scoreset.urn
        return forms

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        experiment = self.kwargs.get('experiment', None)
        if experiment:
            context["experiment_urn"] = experiment.urn
        return context

    def get_scoreset_form_kwargs(self, key):
        return {
            'user': self.request.user,
            'experiment': self.kwargs.get('experiment', None)
        }

    def get_target_gene_form_kwargs(self, key):
        return {'user': self.request.user}


class ScoreSetEditView(ScoreSetAjaxMixin, UpdateDatasetModelView):
    # Overridden from `CreateDatasetModelView`
    # -------
    form_class = ScoreSetForm
    template_name = 'dataset/scoreset/update_scoreset.html'
    model_class_name = 'Score Set'
    model_class = ScoreSet
    # -------

    prefixes = {
        'uniprot_offset_form': 'uniprot',
        'refseq_offset_form': 'refseq',
        'ensembl_offset_form': 'ensembl',
    }
    forms = {
        "scoreset_form": ScoreSetForm,
        "target_gene_form": TargetGeneForm,
        "reference_map_form": PimraryReferenceMapForm,
        "uniprot_offset_form": UniprotOffsetForm,
        "refseq_offset_form": RefseqOffsetForm,
        "ensembl_offset_form": EnsemblOffsetForm,
    }
    restricted_forms = {
        "scoreset_form": ScoreSetEditForm,
    }

    # Dispatch/Post/Get
    # ---------------------------------------------------------------------- #
    @transaction.atomic
    def save_forms(self, forms):
        scoreset_form = forms['scoreset_form']
        scoreset = scoreset_form.save(commit=True)

        if self.instance.private:
            target_gene_form = forms['target_gene_form']
            reference_map_form = forms['reference_map_form']
            uniprot_offset_form = forms['uniprot_offset_form']
            refseq_offset_form = forms['refseq_offset_form']
            ensembl_offset_form = forms['ensembl_offset_form']

            target_gene_form.instance.scoreset = scoreset
            targetgene = target_gene_form.save(commit=True)

            reference_map_form.instance.target = targetgene
            reference_map_form.save(commit=True)

            uniprot_offset_form.save(target=targetgene, commit=True)
            refseq_offset_form.save(target=targetgene, commit=True)
            ensembl_offset_form.save(target=targetgene, commit=True)

        if self.request.POST.get('publish', False):
            propagate = True
            save_parents = True
            scoreset.publish(propagate=True)
            send_admin_email(self.request.user, scoreset)
        else:
            propagate = False
            save_parents = False

        scoreset.set_modified_by(self.request.user, propagate=propagate)
        scoreset.save(save_parents=save_parents)
        assign_user_as_instance_admin(self.request.user, scoreset)
        track_changes(self.request.user, scoreset)
        return forms

    def get_instance_for_form(self, form_key):
        ref_map = None
        uniprot_offset = None
        ensembl_offset = None
        refseq_offset = None
        targetgene = None
        if self.instance.private:
            targetgene = self.instance.get_target()
            if targetgene:
                ref_map = targetgene.get_reference_maps().first()
                uniprot_offset = targetgene.get_uniprot_offset_annotation()
                ensembl_offset = targetgene.get_ensembl_offset_annotation()
                refseq_offset = targetgene.get_refseq_offset_annotation()
        dict_ = {
            'reference_map_form': ref_map,
            'uniprot_offset_form': uniprot_offset,
            'ensembl_offset_form': ensembl_offset,
            'refseq_offset_form': refseq_offset,
            'target_gene_form': targetgene
        }
        return dict_.get(form_key, None)

    def get_scoreset_form_form(self, form_class, **form_kwargs):
        if self.request.method == "POST":
            if self.instance.private:
                return ScoreSetForm.from_request(
                    self.request, self.instance, initial=None,
                    prefix=self.prefixes.get('scoreset_form', None)
                )
            else:
                return ScoreSetEditForm.from_request(
                    self.request, self.instance, initial=None,
                    prefix=self.prefixes.get('scoreset_form', None)
                )
        else:
            if 'user' not in form_kwargs:
                form_kwargs.update({'user': self.request.user})
            return form_class(**form_kwargs)

    def get_uniprot_offset_form_kwargs(self, key):
        return {'instance': self.get_instance_for_form(key)}

    def get_ensembl_offset_form_kwargs(self, key):
        return {'instance': self.get_instance_for_form(key)}

    def get_refseq_offset_form_kwargs(self, key):
        return {'instance': self.get_instance_for_form(key)}

    def get_reference_map_form_kwargs(self, key):
        return {'instance': self.get_instance_for_form(key)}

    def get_target_gene_form_kwargs(self, key):
        return {
            'instance': self.get_instance_for_form(key),
            'user': self.request.user
        }
