import logging

from django.db import transaction

from accounts.permissions import PermissionTypes

from core.utilities.versioning import track_changes

from main.context_processors import baseurl
from metadata.forms import (
    UniprotOffsetForm,
    EnsemblOffsetForm,
    RefseqOffsetForm,
)

# Absolute import tasks for celery to work
from dataset.tasks import create_variants
from dataset import constants

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
        variants = instance.children.all().order_by("hgvs")[:100]
        context["variants"] = variants
        context["score_columns"] = instance.score_columns
        context["count_columns"] = instance.count_columns

        previous_version = instance.previous_version
        if previous_version is not None and previous_version.private and \
                self.request.user not in previous_version.contributors():
            previous_version = instance.previous_public_version
        if previous_version and previous_version.urn == instance.urn:
            previous_version = None

        next_version = instance.next_version
        if next_version is not None and next_version.private and \
                self.request.user not in next_version.contributors():
            next_version = instance.next_public_version
        if next_version and next_version.urn == instance.urn:
            next_version = None

        current_version = instance.current_version
        if current_version is not None and current_version.private and \
                self.request.user not in current_version.contributors():
            current_version = instance.current_public_version
        if current_version and current_version.urn == instance.urn:
            current_version = None
        
        keywords = set([kw for kw in instance.keywords.all()])
        keywords = sorted(
            keywords, key=lambda kw: -1 * kw.get_association_count())
        context['keywords'] = keywords
        context['current_version'] = current_version
        context['previous_version'] = previous_version
        context['next_version'] = next_version
        return context


class ScoreSetCreateView(ScoreSetAjaxMixin, CreateDatasetModelView):
    # Overridden from `CreateDatasetModelView`
    # -------
    form_class = ScoreSetForm
    template_name = 'dataset/scoreset/new_scoreset.html'
    model_class_name = 'Score set'
    # -------

    prefixes = {
        'uniprot_offset': 'uniprot-offset',
        'refseq_offset': 'refseq-offset',
        'ensembl_offset': 'ensembl-offset',
    }
    forms = {
        "scoreset": ScoreSetForm,
        "target_gene": TargetGeneForm,
        "reference_map": PimraryReferenceMapForm,
        "uniprot_offset": UniprotOffsetForm,
        "refseq_offset": RefseqOffsetForm,
        "ensembl_offset": EnsemblOffsetForm,
    }

    def dispatch(self, request, *args, **kwargs):
        if self.request.GET.get("experiment", ""):
            urn = self.request.GET.get("experiment")
            if Experiment.objects.filter(urn=urn).count():
                experiment = Experiment.objects.get(urn=urn)
                has_permission = self.request.user.has_perm(
                    PermissionTypes.CAN_EDIT, experiment)
                if has_permission:
                    self.kwargs['experiment'] = experiment
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def save_forms(self, forms):
        scoreset_form = forms['scoreset']
        target_gene_form = forms['target_gene']
        reference_map_form = forms['reference_map']
        uniprot_offset_form = forms['uniprot_offset']
        refseq_offset_form = forms['refseq_offset']
        ensembl_offset_form = forms['ensembl_offset']

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
            task_kwargs = {
                "user_pk": self.request.user.pk,
                "variants": scoreset_form.get_variants().copy(),
                "scoreset_urn": scoreset.urn,
                "dataset_columns": scoreset_form.dataset_columns.copy(),
            }
            success, _ = create_variants.submit_task(
                kwargs=task_kwargs, request=self.request)

        scoreset.save()
        scoreset.add_administrators(self.request.user)
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
        'uniprot_offset': 'uniprot',
        'refseq_offset': 'refseq',
        'ensembl_offset': 'ensembl',
    }
    forms = {
        "scoreset": ScoreSetForm,
        "target_gene": TargetGeneForm,
        "reference_map": PimraryReferenceMapForm,
        "uniprot_offset": UniprotOffsetForm,
        "refseq_offset": RefseqOffsetForm,
        "ensembl_offset": EnsemblOffsetForm,
    }
    restricted_forms = {
        "scoreset": ScoreSetEditForm,
    }

    # Dispatch/Post/Get
    # ---------------------------------------------------------------------- #
    @transaction.atomic
    def save_forms(self, forms):
        scoreset_form = forms['scoreset']
        scoreset = scoreset_form.save(commit=True)
        scoreset.set_modified_by(self.request.user)
        scoreset.save()

        if self.instance.private:
            target_gene_form = forms['target_gene']
            reference_map_form = forms['reference_map']
            uniprot_offset_form = forms['uniprot_offset']
            refseq_offset_form = forms['refseq_offset']
            ensembl_offset_form = forms['ensembl_offset']

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
            task_kwargs = dict(
                user_pk=self.request.user.pk,
                variants=scoreset_form.get_variants().copy(),
                scoreset_urn=scoreset.urn,
                dataset_columns=scoreset_form.dataset_columns.copy(),
                base_url=baseurl(self.request)['BASE_URL'],
            )
            success, _ = create_variants.submit_task(
                kwargs=task_kwargs, request=self.request)

        scoreset.save()
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
            'reference_map': ref_map,
            'uniprot_offset': uniprot_offset,
            'ensembl_offset': ensembl_offset,
            'refseq_offset': refseq_offset,
            'target_gene': targetgene
        }
        return dict_.get(form_key, None)

    def get_scoreset_form(self, form_class, **form_kwargs):
        if self.request.method == "POST":
            if self.instance.private:
                return ScoreSetForm.from_request(
                    self.request, self.instance, initial=None,
                    prefix=self.prefixes.get('scoreset', None)
                )
            else:
                return ScoreSetEditForm.from_request(
                    self.request, self.instance, initial=None,
                    prefix=self.prefixes.get('scoreset', None)
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
