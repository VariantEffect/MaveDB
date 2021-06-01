# -*- coding: UTF-8 -*-

import json
import logging
from typing import Tuple, List, Optional, Dict, Union

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponse

from accounts.permissions import user_is_anonymous, PermissionTypes

from core.utilities import is_null
from core.utilities.pandoc import convert_md_to_html
from dataset.models import ExperimentSet, ScoreSet

from dataset.models import DatasetModel
from dataset.models.experiment import Experiment

from genome.models import TargetGene, ReferenceMap
from genome.serializers import TargetGeneSerializer

logger = logging.getLogger("django")


class DatasetPermissionMixin(PermissionRequiredMixin):
    """
    Overrides the `has_permission` method of `PermissionRequiredMixin`.
    Returns
    """

    VIEW_PERMISSION = f"dataset.{PermissionTypes.CAN_VIEW}"
    EDIT_PERMISSION = f"dataset.{PermissionTypes.CAN_EDIT}"
    MANAGE_PERMISSION = f"dataset.{PermissionTypes.CAN_MANAGE}"

    redirect_unauthenticated_users = "/login/"
    login_url = "/login/"
    raise_exception = True
    permission_required = VIEW_PERMISSION

    def has_permission_for_meta(self, instance, user) -> bool:
        """
        Returns `True` if a user can view any of this dataset's
        meta analysis score sets children. Children may not be directly
        descendant as in the case for experiment sets.
        """
        if isinstance(instance, (Experiment, ExperimentSet)):
            if instance.is_mixed_meta_analysis:
                # Check special case where instance is an experiment/set with
                # a mix of meta-analyses and regular score sets. This can happen
                # when a score set meta-analyses only one score set, so the
                # meta-analysis inherits the parent score set's experiment set.
                # These parents are treated as regular datasets.
                return user.has_perms(self.get_permission_required(), instance)
            else:
                # Otherwise check if user can access at least one of the score
                # set meta-analyses as a viewer. Parents to meta-analyses can
                # only be viewed.
                metas = getattr(
                    instance,
                    "meta_analysis_scoresets",
                    ScoreSet.objects.none(),
                )
                can_access_at_least_one_meta_scoreset = any(
                    user.has_perm(self.VIEW_PERMISSION, s) for s in metas
                )
                return (
                    self.permission_required == self.VIEW_PERMISSION
                    and can_access_at_least_one_meta_scoreset
                )
        else:
            return user.has_perms(self.get_permission_required(), instance)

    def has_permission(self):
        """
        Returns `False` if the user is anonymous. `True` if an authenticated
        user has permissions on a private dataset or `False` otherwise.
        """
        instance: DatasetModel = self.get_object()
        is_public = not instance.private
        is_private = instance.private

        user = self.request.user
        anon_user = user_is_anonymous(user)
        perm = self.permission_required

        is_meta_analysis = instance.is_meta_analysis
        is_mixed_analysis = getattr(instance, "is_mixed_meta_analysis", False)

        if is_private and anon_user:
            return False
        elif is_public and self.permission_required == self.VIEW_PERMISSION:
            return True
        elif is_private and perm != self.VIEW_PERMISSION and anon_user:
            return False
        elif is_meta_analysis or is_mixed_analysis:
            return self.has_permission_for_meta(instance, user)
        else:
            return user.has_perms(self.get_permission_required(), instance)


class DatasetFormViewContextMixin:
    """
    Overrides the `get_context_data` function from form-based Django class
    based views.
    """

    def get_context_data(self, **kwargs):
        """
        Inserts common context parameters into a context which javascript
        uses to dynamically populate select fields of invalid submissions.
        """
        context = super().get_context_data(**kwargs)

        if self.request.method == "POST":
            # Get the new keywords/urn/target org so that we can return
            # them for list re-population if the form has errors.
            keywords = self.request.POST.getlist("keywords", [])
            keywords = [kw for kw in keywords if not is_null(kw)]

            sra_ids = self.request.POST.getlist("sra_ids", [])
            sra_ids = [i for i in sra_ids if not is_null(i)]

            doi_ids = self.request.POST.getlist("doi_ids", [])
            doi_ids = [i for i in doi_ids if not is_null(i)]

            pubmed_ids = self.request.POST.getlist("pubmed_ids", [])
            pubmed_ids = [i for i in pubmed_ids if not is_null(i)]

            uniprot_id = self.request.POST.getlist(
                "uniprot-offset-identifier", []
            )
            uniprot_id = [i for i in uniprot_id if not is_null(i)]

            ensembl_id = self.request.POST.getlist(
                "ensembl-offset-identifier", []
            )
            ensembl_id = [i for i in ensembl_id if not is_null(i)]

            refseq_id = self.request.POST.getlist(
                "refseq-offset-identifier", []
            )
            refseq_id = [i for i in refseq_id if not is_null(i)]

            context["repop_keywords"] = ",".join(keywords)
            context["repop_sra_identifiers"] = ",".join(sra_ids)
            context["repop_doi_identifiers"] = ",".join(doi_ids)
            context["repop_pubmed_identifiers"] = ",".join(pubmed_ids)
            context["repop_uniprot_identifier"] = ",".join(uniprot_id)
            context["repop_ensembl_identifier"] = ",".join(ensembl_id)
            context["repop_refseq_identifier"] = ",".join(refseq_id)

        context["clearable_fields"] = [
            "Variant score data",
            "Variant count data",
            "Metadata",
            "FASTA file",
        ]

        return context


class DataSetAjaxMixin:
    def get_ajax(
        self, return_dict=False, *args, **kwargs
    ) -> Union[Dict, HttpResponse]:
        # If the request is ajax, then it's for previewing the abstract
        # or method description. This code is coupled with base.js. Changes
        # here might break the javascript code.
        data = {}
        if "abstractText" in self.request.GET:
            data.update(
                {
                    "abstractText": convert_md_to_html(
                        self.request.GET.get("abstractText", "")
                    )
                }
            )
        if "methodText" in self.request.GET:
            data.update(
                {
                    "methodText": convert_md_to_html(
                        self.request.GET.get("methodText", "")
                    )
                }
            )
        if return_dict:
            return data
        else:
            return HttpResponse(
                json.dumps(data), content_type="application/json"
            )


class ExperimentAjaxMixin(DataSetAjaxMixin):
    pass


class ExperimentSetAjaxMixin(DataSetAjaxMixin):
    pass


class ScoreSetAjaxMixin(DataSetAjaxMixin):
    """
    Simple mixin to serialize a target gene for form target autocomplete and
    also to obtain the scoresets for a selected experiment to dynamically fill
    the replaces options with allowable selections.
    """

    def get_ajax(self, *args, **kwargs) -> HttpResponse:
        # If the request is ajax, then it's for previewing the abstract
        # or method description. This code is coupled with base.js. Changes
        # here might break the javascript code.
        data = super().get_ajax(return_dict=True, *args, **kwargs)

        if "targetId" in self.request.GET:
            pk = self.request.GET.get("targetId", "")
            if pk and TargetGene.objects.filter(pk=pk).count():
                target: TargetGene = TargetGene.objects.get(pk=pk)
                data.update(TargetGeneSerializer(target).data)

                ref_map: Optional[ReferenceMap] = target.reference_maps.first()
                if ref_map is not None:
                    data["genome"] = ref_map.genome.pk

        if "experiment" in self.request.GET:
            pk = self.request.GET.get("experiment", "")
            if pk and Experiment.objects.filter(pk=pk).count():
                experiment: Experiment = Experiment.objects.get(pk=pk)
                scoresets = [
                    (s.pk, s.urn, s.title)
                    for s in experiment.scoresets.order_by("urn")
                    if self.request.user.has_perm(PermissionTypes.CAN_EDIT, s)
                    and not s.private
                ]
                data.update({"scoresets": scoresets})
                data.update(
                    {"keywords": [k.text for k in experiment.keywords.all()]}
                )

        return HttpResponse(json.dumps(data), content_type="application/json")


class PrivateDatasetFilterMixin:
    """
    Splits datasets into those viewable, filtering out those that are not.
    """

    def filter_and_split_instances(
        self, instances
    ) -> Tuple[List[DatasetModel], List[DatasetModel]]:

        private_viewable: List[DatasetModel] = []
        public: List[DatasetModel] = []

        for instance in instances:
            if user_is_anonymous(self.request.user) and instance.private:
                continue

            has_perm = self.request.user.has_perm(
                PermissionTypes.CAN_VIEW, instance
            )
            if not instance.private:
                public.append(instance)
            elif instance.private and has_perm:
                private_viewable.append(instance)
        return public, private_viewable
