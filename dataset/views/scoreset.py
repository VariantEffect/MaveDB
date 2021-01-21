# -*- coding: UTF-8 -*-

import logging
from typing import Dict, Any, Optional

from django.contrib import messages
from django.db import transaction
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.urls import reverse

from reversion import create_revision

from accounts.models import Profile
from accounts.permissions import PermissionTypes

from genome.models import TargetGene

from metadata.forms import (
    UniprotOffsetForm,
    EnsemblOffsetForm,
    RefseqOffsetForm,
)

# Absolute import tasks for celery to work
from dataset.tasks import create_variants
from dataset import constants

from genome.forms import PrimaryReferenceMapForm, TargetGeneForm

from ..models.scoreset import ScoreSet
from ..models.experiment import Experiment
from ..forms.scoreset import ScoreSetForm, ScoreSetEditForm
from ..mixins import ScoreSetAjaxMixin

from .base import (
    DatasetModelView,
    CreateDatasetView,
    UpdateDatasetView,
)

logger = logging.getLogger("django")
User = get_user_model()


class ScoreSetDetailView(DatasetModelView):
    """
    Simple detail view. See `scoreset/scoreset.html` for the template
    layout.
    """

    # Overriding from `DatasetModelView`.
    # -------
    model = ScoreSet
    template_name = "dataset/scoreset/scoreset.html"
    slug_url_kwarg = "urn"
    slug_field = "urn"
    # -------

    def get_context_data(self, **kwargs):
        context = super(ScoreSetDetailView, self).get_context_data(**kwargs)
        instance = self.get_object()
        order_by = "id"  # instance.primary_hgvs_column
        variants = instance.children.order_by("{}".format(order_by))[:10]
        context["variants"] = variants
        context["score_columns"] = instance.score_columns
        context["count_columns"] = instance.count_columns

        current_version = instance.get_current_version(self.request.user)
        previous_version = instance.get_previous_version(self.request.user)
        next_version = instance.get_next_version(self.request.user)

        keywords = set([kw for kw in instance.keywords.all()])
        keywords = sorted(
            keywords, key=lambda kw: -1 * kw.get_association_count()
        )
        context["keywords"] = keywords
        context["current_version"] = current_version
        context["previous_version"] = previous_version
        context["next_version"] = next_version
        context["next_version"] = next_version
        context["meta_analysed_by"] = instance.meta_analysed_by.all()
        context["meta_analysis_for"] = instance.meta_analysis_for.all()
        context["is_meta_analysis"] = instance.is_meta_analysis
        context["is_meta_analysed"] = instance.is_meta_analysed

        return context

    def get_ajax(self, *args, **kwargs):
        type_ = self.request.GET.get("type", False)
        instance = self.get_object()

        order_by = "id"  # instance.primary_hgvs_column
        variants = instance.children.order_by("{}".format(order_by))[:10]

        # Format table columns for dataTables
        columns = (
            instance.count_columns
            if type_ == "counts"
            else instance.score_columns
        )
        table_columns = []
        for i, name in enumerate(columns):
            table_columns.append({"className": name, "targets": [i]})

        rows = []
        for variant in variants:
            row = {}
            if type_ == "counts":
                v_data = variant.count_data
            else:
                v_data = variant.score_data

            for i, data in enumerate(v_data):
                if isinstance(data, float):
                    data = "{:.3f}".format(data)
                elif isinstance(data, int):
                    data = "{:.6g}".format(data)
                elif not data or data is None:
                    data = str(None)
                else:
                    data = data
                row["{}".format(i)] = data
            rows.append(row)

        response = {
            "draw": 1,
            "data": rows,
            "recordsTotal": len(rows),
            "recordsFiltered": len(rows),
            "columns": table_columns,
        }
        return JsonResponse(response, safe=False)


class BaseScoreSetFormView(ScoreSetAjaxMixin):
    # Override these in update/create
    model = None
    form_class = None

    def get(self, *args, **kwargs) -> HttpResponse:
        download_errors = "errors_for" in self.request.GET
        if download_errors:
            e_type = self.request.GET.get("errors_for")
            errors = None
            profile: Profile = self.request.user.profile
            if e_type == "score_data":
                errors = profile.get_submission_scores_errors()
            elif e_type == "count_data":
                errors = profile.get_submission_counts_errors()
            else:
                logger.warning(f"Unknown error type '{e_type}'")

            if errors:
                response = HttpResponse(
                    content="\n".join(errors), content_type="plain/text"
                )
                response[
                    "Content-Disposition"
                ] = f'attachment; filename="{e_type}_errors.txt"'
                return response

        return super().get(*args, **kwargs)

    def form_valid(self, form: Dict[str, Any]) -> HttpResponseRedirect:
        try:
            profile = self.request.user.profile
            profile.clear_submission_errors()
            profile.save()

            self.save_forms(form)
            messages.success(self.request, self.get_success_message())
        except Exception as error:
            logger.exception(
                f"The following error occurred during "
                f"{self.model.__name__} creation:\n{str(error)}"
            )
            messages.error(
                self.request,
                "There was a server side error while saving your submission. "
                "Please contact support if this issue persists.",
            )
            return self.render_to_response(self.get_context_data(**form))

        return HttpResponseRedirect(
            reverse("dataset:scoreset_detail", kwargs={"urn": self.object.urn})
        )

    def form_invalid(self, form: Dict[str, Any]):
        ss_form: ScoreSetForm = form.get("scoreset_form")
        profile: Profile = self.request.user.profile
        if ss_form.should_write_scores_error_file and ss_form.scores_dataset:
            profile.set_submission_scores_errors(
                data=ss_form.scores_dataset.errors
            )
        else:
            profile.set_submission_scores_errors(data=None)

        if ss_form.should_write_counts_error_file and ss_form.counts_dataset:
            profile.set_submission_counts_errors(
                data=ss_form.counts_dataset.errors
            )
        else:
            profile.set_submission_counts_errors(data=None)

        profile.save()

        messages.error(
            self.request,
            "Your submission contains errors. Please address each one before"
            "re-submitting.",
        )

        return self.render_to_response(self.get_context_data(**form))

    def get_success_message(self) -> str:
        raise NotImplementedError()

    # --------------- Helpers ------------------------------------------- #
    @transaction.atomic()
    def save_forms(self, forms: Dict[str, Any]) -> Dict[str, Any]:
        scoreset_form: ScoreSetForm = forms["scoreset_form"]

        with create_revision():
            scoreset: ScoreSet = scoreset_form.save(commit=True)
            self.object: ScoreSet = scoreset

        # Creating a new scoreset or editing a private scoreset, otherwise only
        # the score set form will be served.
        if self.object.private:
            target_form: TargetGeneForm = forms["target_gene_form"]
            reference_map_form: PrimaryReferenceMapForm = forms[
                "reference_map_form"
            ]
            uniprot_offset_form: UniprotOffsetForm = forms[
                "uniprot_offset_form"
            ]
            refseq_offset_form: RefseqOffsetForm = forms["refseq_offset_form"]
            ensembl_offset_form: EnsemblOffsetForm = forms[
                "ensembl_offset_form"
            ]

            target: TargetGene = target_form.save(
                commit=True, scoreset=scoreset
            )

            reference_map_form.instance.target = target
            reference_map_form.save(commit=True)

            uniprot_offset = uniprot_offset_form.save(
                target=target,
                commit=True,
            )
            refseq_offset = refseq_offset_form.save(
                target=target,
                commit=True,
            )
            ensembl_offset = ensembl_offset_form.save(
                target=target,
                commit=True,
            )

            if uniprot_offset:
                target.uniprot_id = uniprot_offset.identifier
            else:
                target.uniprot_id = None

            if refseq_offset:
                target.refseq_id = refseq_offset.identifier
            else:
                target.refseq_id = None

            if ensembl_offset:
                target.ensembl_id = ensembl_offset.identifier
            else:
                target.ensembl_id = None

            target.save()

        return forms

    def submit_job(self, form: ScoreSetForm):
        if form.has_variants() and self.object.private:
            logger.info(
                "Submitting task from {} for {} to Celery.".format(
                    self.request.user, self.object.urn
                )
            )

            self.object.processing_state = constants.processing
            self.object.save()

            scores_rs, counts_rs, index = form.serialize_variants()
            task_kwargs = {
                "user_pk": self.request.user.pk,
                "scoreset_urn": self.object.urn,
                "dataset_columns": form.dataset_columns.copy(),
                "index": index,
                "scores_records": scores_rs,
                "counts_records": counts_rs,
            }

            success, _ = create_variants.submit_task(
                request=self.request,
                kwargs=task_kwargs,
            )

            logger.info(
                "Submission to celery from {} for {}: {}".format(
                    self.request.user, self.object.urn, success
                )
            )

            if not success:
                self.object.processing_state = constants.failed
                self.object.save()


class ScoreSetCreateView(BaseScoreSetFormView, CreateDatasetView):
    """
    This view serves the forms:
        - `ScoreSetForm`
        - `TargetGeneForm`
        - `PrimaryReferenceMapForm`
        - `UniprotOffsetForm`
        - `RefseqOffsetForm`
        - `EnsemblOffsetForm`

    Raises
    ------
    Http404
    PermissionDenied
    """

    # Overridden from `CreateDatasetModelView`
    # -------
    model = ScoreSet
    form_class = ScoreSetForm
    template_name = "dataset/scoreset/new_scoreset.html"
    # -------

    def dispatch(self, request, *args, **kwargs) -> HttpResponseRedirect:
        self.parent: Optional[Experiment] = None

        if self.request.GET.get("experiment", ""):
            urn = self.request.GET.get("experiment")
            if Experiment.objects.filter(urn=urn).count():
                # TODO: allow if public
                experiment = Experiment.objects.get(urn=urn)
                has_permission = (
                    self.request.user.has_perm(
                        PermissionTypes.CAN_EDIT, experiment
                    )
                    or not experiment.private
                )
                if has_permission:
                    self.parent: Optional[Experiment] = experiment

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        # Store reference to object that will be created later
        self.object = None

        forms = self.get_form()
        valid = True

        target_form: TargetGeneForm = forms.pop("target_gene_form")
        valid &= target_form.is_valid()

        scoreset_form: ScoreSetForm = forms.pop("scoreset_form")
        valid &= scoreset_form.is_valid(targetseq=target_form.get_targetseq())

        # Check that if AA sequence, dataset defined pro variants only.
        if (
            target_form.sequence_is_protein
            and not scoreset_form.allow_aa_sequence
        ):
            valid = False
            target_form.add_error(
                "sequence_text",
                "Protein sequences are allowed if your data set exclusively  "
                "defines protein variants.",
            )

        # Check remaining forms which do not need special treatment
        valid &= all(form.is_valid() for _, form in forms.items())

        # Put forms back into forms dictionary.
        forms["scoreset_form"] = scoreset_form
        forms["target_gene_form"] = target_form

        if valid:
            return self.form_valid(forms)
        else:
            return self.form_invalid(forms)

    def get_form(self, form_class=None) -> Dict[str, Any]:
        return {
            "scoreset_form": self.get_scoreset_form(),
            "target_gene_form": self.get_target_form(),
            "reference_map_form": self.get_reference_map_form(),
            "uniprot_offset_form": self.get_uniprot_offset_form(),
            "refseq_offset_form": self.get_refseq_offset_form(),
            "ensembl_offset_form": self.get_ensembl_offset_form(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Unpack all the individual forms into the context dictionary
        # but don't override if the form is already in there.
        for name, form in context.pop("form", {}).items():
            if name not in context:
                context[name] = form

        if self.parent is not None:
            context["experiment_urn"] = self.parent.urn

        return context

    @transaction.atomic()
    def save_forms(self, forms: Dict[str, Any]) -> Dict[str, Any]:
        """Called by form_valid when all forms are ready to be saved."""
        forms = super().save_forms(forms=forms)
        ss_form: ScoreSetForm = forms["scoreset_form"]

        self.object.add_administrators(self.request.user)
        # assign_superusers_as_admin(scoreset)
        self.kwargs["urn"] = self.object.urn

        transaction.on_commit(lambda: self.submit_job(form=ss_form))

        return forms

    def get_success_message(self) -> str:
        return (
            f"Successfully created a new Score set with temporary accession "
            f"number {self.object.urn}. Uploaded files are being processed "
            f"and further editing has been temporarily disabled. Please check "
            f"back later."
        )

    def get_scoreset_form(self) -> ScoreSetForm:
        kwargs = {"user": self.request.user, "experiment": self.parent}
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST
            kwargs["files"] = self.request.FILES
        return ScoreSetForm(**kwargs)

    def get_target_form(self) -> TargetGeneForm:
        kwargs = {"user": self.request.user}
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST
            kwargs["files"] = self.request.FILES
        return TargetGeneForm(**kwargs)

    def get_uniprot_offset_form(self) -> UniprotOffsetForm:
        kwargs = {"prefix": "uniprot-offset"}
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST
        return UniprotOffsetForm(**kwargs)

    def get_ensembl_offset_form(self) -> EnsemblOffsetForm:
        kwargs = {"prefix": "ensembl-offset"}
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST
        return EnsemblOffsetForm(**kwargs)

    def get_refseq_offset_form(self) -> RefseqOffsetForm:
        kwargs = {"prefix": "refseq-offset"}
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST
        return RefseqOffsetForm(**kwargs)

    def get_reference_map_form(self):
        kwargs = {}
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST
        return PrimaryReferenceMapForm(**kwargs)


class ScoreSetEditView(BaseScoreSetFormView, UpdateDatasetView):
    """
    This view serves the forms:
        - `ScoreSetForm`
        - `TargetGeneForm`
        - `PrimaryReferenceMapForm`
        - `UniprotOffsetForm`
        - `RefseqOffsetForm`
        - `EnsemblOffsetForm`

    Unless the instance is already public, then it will only serve:
        -   ScoreSetForm`

    Raises
    ------
    Http404
    PermissionDenied
    """

    # Overridden from `UpdateDatasetView`
    # -------
    model = ScoreSet
    template_name = "dataset/scoreset/update_scoreset.html"
    slug_field = "urn"
    slug_url_kwarg = "urn"

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        # Store reference to object that will be created later
        self.object: ScoreSet = self.get_object()

        forms = self.get_form()
        valid = True

        if self.object.private:
            target_form: TargetGeneForm = forms.pop("target_gene_form")
            scoreset_form: ScoreSetForm = forms.pop("scoreset_form")

            valid &= target_form.is_valid()

            if not self.object.get_target().match_sequence(
                sequence=target_form.get_targetseq()
            ):
                # Changed sequence. Request new files.
                if not self.request.FILES.get("score_data"):
                    target_form.add_error(
                        None,
                        "Please re-upload your scores and counts files if you "
                        "are altering the target sequence.",
                    )
                    valid = False

            valid &= scoreset_form.is_valid(
                targetseq=target_form.get_targetseq()
            )

            # Check that if AA sequence, dataset defined pro variants only,
            # but only if new files have been uploaded.
            if (
                target_form.sequence_is_protein
                and scoreset_form.has_variants()
                and not scoreset_form.allow_aa_sequence
            ):
                valid = False
                target_form.add_error(
                    "sequence_text",
                    "Protein sequences are allowed if your data set "
                    "exclusively defines protein variants.",
                )

            # Check remaining forms which do not need special treatment
            valid &= all(form.is_valid() for _, form in forms.items())

            # Put forms back into forms dictionary just in case
            forms["scoreset_form"] = scoreset_form
            forms["target_gene_form"] = target_form
        else:
            scoreset_form: ScoreSetForm = forms.pop("scoreset_form")
            valid &= scoreset_form.is_valid()

        if valid:
            return self.form_valid(forms)
        else:
            return self.form_invalid(forms)

    @transaction.atomic()
    def save_forms(self, forms: Dict[str, Any]) -> Dict[str, Any]:
        """Called by form_valid when all forms are ready to be saved."""
        forms = super().save_forms(forms=forms)
        ss_form: ScoreSetForm = forms["scoreset_form"]

        # Call celery task after all the above has successfully completed
        transaction.on_commit(lambda: self.submit_job(form=ss_form))

        return forms

    def get_form(self, form_class=None) -> Dict[str, Any]:
        if self.object.private:
            return {
                "scoreset_form": self.get_scoreset_form(),
                "target_gene_form": self.get_target_form(),
                "reference_map_form": self.get_reference_map_form(),
                "uniprot_offset_form": self.get_uniprot_offset_form(),
                "refseq_offset_form": self.get_refseq_offset_form(),
                "ensembl_offset_form": self.get_ensembl_offset_form(),
            }
        else:
            return {"scoreset_form": self.get_scoreset_form()}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Unpack all the individual forms into the context dictionary
        # but don't override if the form is already in there.
        for name, form in context.pop("form", {}).items():
            if name not in context:
                context[name] = form

        return context

    def get_success_message(self) -> str:
        if self.object.processing_state == constants.processing:
            return (
                f"Successfully updated {self.object.urn}. Uploaded files are "
                f"being processed and further editing has been temporarily "
                f"disabled. Please check back later."
            )
        else:
            return f"Successfully updated {self.object.urn}."

    def get_scoreset_form(self) -> ScoreSetForm:
        kwargs = {"user": self.request.user, "instance": self.object}
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST
            kwargs["files"] = self.request.FILES

        if self.object.private:
            form_class = ScoreSetForm
        else:
            form_class = ScoreSetEditForm

        return form_class(**kwargs)

    def get_target_form(self) -> TargetGeneForm:
        kwargs = {
            "instance": self._get_instance_for_form("target_gene_form"),
            "user": self.request.user,
        }
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST
            kwargs["files"] = self.request.FILES

        return TargetGeneForm(**kwargs)

    def get_uniprot_offset_form(self) -> UniprotOffsetForm:
        kwargs = {
            "instance": self._get_instance_for_form("uniprot_offset_form"),
            "prefix": "uniprot-offset",
        }
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST

        return UniprotOffsetForm(**kwargs)

    def get_ensembl_offset_form(self) -> EnsemblOffsetForm:
        kwargs = {
            "instance": self._get_instance_for_form("ensembl_offset_form"),
            "prefix": "ensembl-offset",
        }
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST

        return EnsemblOffsetForm(**kwargs)

    def get_refseq_offset_form(self) -> RefseqOffsetForm:
        kwargs = {
            "instance": self._get_instance_for_form("refseq_offset_form"),
            "prefix": "refseq-offset",
        }
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST

        return RefseqOffsetForm(**kwargs)

    def get_reference_map_form(self) -> PrimaryReferenceMapForm:
        kwargs = {
            "instance": self._get_instance_for_form("reference_map_form")
        }
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST

        return PrimaryReferenceMapForm(**kwargs)

    def _get_instance_for_form(self, form_key):
        ref_map = None
        uniprot_offset = None
        ensembl_offset = None
        refseq_offset = None
        target = None

        if self.object and self.object.private:
            target = self.object.get_target()
            if target:
                ref_map = target.get_reference_maps().first()
                uniprot_offset = target.get_uniprot_offset_annotation()
                ensembl_offset = target.get_ensembl_offset_annotation()
                refseq_offset = target.get_refseq_offset_annotation()

        dict_ = {
            "reference_map_form": ref_map,
            "uniprot_offset_form": uniprot_offset,
            "ensembl_offset_form": ensembl_offset,
            "refseq_offset_form": refseq_offset,
            "target_gene_form": target,
        }

        return dict_.get(form_key, None)
