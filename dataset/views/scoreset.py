import logging

from django.db import transaction

from accounts.permissions import (
    PermissionTypes, assign_user_as_instance_admin
)

from core.utilities.versioning import track_changes

from main.context_processors import baseurl
from metadata.forms import (
    UniprotOffsetForm,
    EnsemblOffsetForm,
    RefseqOffsetForm,
)

from genome.forms import PimraryReferenceMapForm, TargetGeneForm

from dataset import constants
# Absolute import tasks for celery to work
from dataset.tasks import create_variants, publish_scoreset
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
        variants = instance.children.all().order_by("hgvs")[:100]
        context["variants"] = variants
        context["score_columns"] = instance.score_columns
        context["count_columns"] = instance.count_columns
        
        keywords = set([kw for kw in instance.keywords.all()])
        keywords = sorted(keywords, key=lambda kw: -1 * kw.get_association_count())
        context['keywords'] = keywords
        
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
        scoreset.set_created_by(self.request.user)
        scoreset.set_modified_by(self.request.user)
        scoreset.save()

        target_gene_form.instance.scoreset = scoreset
        targetgene = target_gene_form.save(commit=True)

        reference_map_form.instance.target = targetgene
        reference_map_form.save(commit=True)

        uniprot_offset = \
            uniprot_offset_form.save(target=targetgene, commit=True)
        refseq_offset = \
            refseq_offset_form.save(target=targetgene, commit=True)
        ensembl_offset = \
            ensembl_offset_form.save(target=targetgene, commit=True)

        if uniprot_offset:
            targetgene.uniprot_id = uniprot_offset.identifier
        if refseq_offset:
            targetgene.refseq_id = refseq_offset.identifier
        if ensembl_offset:
            targetgene.ensembl_id = ensembl_offset.identifier
        targetgene.save()

        # Call celery task after all the above has successfully completed
        if scoreset_form.get_variants():
            scoreset.processing_state = constants.processing
            scoreset.save()
            create_variants_kwargs = {
                "user_pk": self.request.user.pk,
                "variants": scoreset_form.get_variants().copy(),
                "scoreset_urn": scoreset.urn,
                "dataset_columns": scoreset_form.dataset_columns.copy(),
                "base_url": baseurl(self.request)['BASE_URL'],
            }
            create_variants.delay(**create_variants_kwargs)

        assign_user_as_instance_admin(self.request.user, scoreset)
        track_changes(instance=scoreset, user=self.request.user)
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
        publish = bool(self.request.POST.get('publish', False))
        scoreset_form = forms['scoreset_form']
        scoreset = scoreset_form.save(commit=True)
        scoreset.set_modified_by(self.request.user)
        scoreset.save()

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

            uniprot_offset = \
                uniprot_offset_form.save(target=targetgene, commit=True)
            refseq_offset = \
                refseq_offset_form.save(target=targetgene, commit=True)
            ensembl_offset = \
                ensembl_offset_form.save(target=targetgene, commit=True)

            if uniprot_offset:
                targetgene.uniprot_id = uniprot_offset.identifier
            if refseq_offset:
                targetgene.refseq_id = refseq_offset.identifier
            if ensembl_offset:
                targetgene.ensembl_id = ensembl_offset.identifier
            targetgene.save()

        # Call celery task after all the above has successfully completed
        if scoreset_form.get_variants():
            scoreset.processing_state = constants.processing
            scoreset.save()
            create_variants.delay(
                user_pk=self.request.user.pk,
                variants=scoreset_form.get_variants().copy(),
                scoreset_urn=scoreset.urn,
                publish=publish,
                dataset_columns=scoreset_form.dataset_columns.copy(),
                base_url=baseurl(self.request)['BASE_URL'],
            )
        elif (not scoreset_form.get_variants()) and publish:
            publish_scoreset.delay(
                scoreset_urn=scoreset.urn,
                user_pk=self.request.user.pk,
                base_url=baseurl(self.request)['BASE_URL'],
            )

        assign_user_as_instance_admin(self.request.user, scoreset)
        track_changes(instance=scoreset, user=self.request.user)
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
