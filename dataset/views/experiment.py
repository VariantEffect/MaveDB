# -*- coding: UTF-8 -*-

import logging
from typing import Optional, Type, Union

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.db import transaction

from reversion import create_revision

from accounts.permissions import PermissionTypes
from ..forms.base import DatasetModelForm

from ..forms.experiment import ExperimentForm, ExperimentEditForm
from ..models.experiment import Experiment
from ..models.experimentset import ExperimentSet
from ..mixins import ExperimentAjaxMixin

from .base import (
    DatasetModelView,
    CreateDatasetView,
    UpdateDatasetView,
)

logger = logging.getLogger("django")


class ExperimentDetailView(DatasetModelView):
    """
    object in question and render a simple template for public viewing, or
    Simple class-based detail view for an `Experiment`. Will either find the
    404.
    """

    # Overriding from `DatasetModelView`.
    # -------
    model = Experiment
    template_name = "dataset/experiment/experiment.html"
    # -------

    def dispatch(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_meta_analysis:
            kwargs["urn"] = instance.parent.urn
            return redirect("dataset:experimentset_detail", *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = self.get_object()
        keywords = set([kw for kw in instance.keywords.all()])
        keywords = sorted(
            keywords, key=lambda kw: -1 * kw.get_association_count()
        )
        context["keywords"] = keywords
        return context


class ExperimentCreateView(ExperimentAjaxMixin, CreateDatasetView):
    """
    This view serves up the form:
        - `ExperimentForm` for the instantiation of an Experiment instance.

    A new experiment instance will only be created if all forms pass validation
    otherwise the forms with the appropriate errors will be served back. Upon
    success, the user is redirected to the newly created experiment page.
    """

    # Overridden from `CreateDatasetModelView`
    # -------
    model = Experiment
    form_class = ExperimentForm
    template_name = "dataset/experiment/new_experiment.html"
    # -------

    def dispatch(self, request, *args, **kwargs):
        self.parent: Optional[ExperimentSet] = None

        # User has requested to prefill experimentset dropdown, form logic
        # will handle this during creation of a new form.
        if self.request.GET.get("experimentset", ""):
            urn = self.request.GET.get("experimentset")
            if ExperimentSet.objects.filter(urn=urn).count():
                experimentset = ExperimentSet.objects.get(urn=urn)
                has_permission = self.request.user.has_perm(
                    PermissionTypes.CAN_EDIT, experimentset
                )
                if has_permission:
                    self.parent = experimentset

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form: DatasetModelForm) -> HttpResponseRedirect:
        try:
            with create_revision():
                response = super().form_valid(form)
                self.object.parent.save()

            self.post_save()

            messages.success(
                self.request,
                f"Successfully created a new {self.model.__name__}, which "
                f"has been assigned a temporary accession number "
                f"{self.object.urn}.",
            )

            return response
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
            return super().form_invalid(form)

    def form_invalid(self, form: DatasetModelForm):
        messages.error(
            self.request,
            "Your submission contains errors. Please address each one before"
            "re-submitting.",
        )
        return super().form_invalid(form)

    @transaction.atomic
    def post_save(self) -> None:
        experiment: Experiment = self.object

        # Save and update permissions. If no experimentset was selected,
        # by default a new experimentset is created with the current user
        # as it's administrator.
        experiment.add_administrators(self.request.user)
        if not self.request.POST["experimentset"]:
            experiment.parent.add_administrators(self.request.user)

        # assign_superusers_as_admin(experiment)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["experimentset"] = self.parent
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["experiment_form"] = context.pop("form")
        return context

    def get_success_url(self):
        return "{}{}".format(
            reverse_lazy("dataset:scoreset_new"),
            "?experiment={}".format(self.object.urn),
        )


class ExperimentEditView(ExperimentAjaxMixin, UpdateDatasetView):
    """
    This view serves up the form:
        - `ExperimentForm` for the instantiation of an Experiment instance.

    A new experiment instance will only be created if all forms pass validation
    otherwise the forms with the appropriate errors will be served back. Upon
    success, the user is redirected to the newly created experiment page.
    """

    # Overridden from `CreateDatasetModelView`
    # -------
    model = Experiment
    # More than one type of form might be served so override get_form completely
    form_class = None
    template_name = "dataset/experiment/update_experiment.html"
    # -------

    def form_valid(self, form: DatasetModelForm) -> HttpResponseRedirect:
        try:
            with create_revision():
                response = super().form_valid(form)

            self.post_save()

            messages.success(
                self.request, f"Experiment {self.object.urn} has been updated."
            )

            return response
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
            return super().form_invalid(form)

    def form_invalid(self, form: DatasetModelForm):
        messages.error(
            self.request,
            "Your submission contains errors. Please address each one before"
            "re-submitting.",
        )
        return super().form_invalid(form)

    def get_form_class(
        self,
    ) -> Type[Union[ExperimentForm, ExperimentEditForm]]:
        if self.object.private:
            return ExperimentForm
        else:
            return ExperimentEditForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["experiment_form"] = context.pop("form")
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    @transaction.atomic
    def post_save(self) -> None:
        return
