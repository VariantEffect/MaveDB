# -*- coding: UTF-8 -*-

import logging

from django.views.generic import DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import reverse
from django.contrib import messages
from django.http import HttpResponseRedirect

from core.mixins import AjaxView
from dataset import constants
from dataset.mixins import (
    DatasetPermissionMixin,
    DatasetFormViewContextMixin,
)

logger = logging.getLogger("django")


class DatasetModelView(DatasetPermissionMixin, AjaxView, DetailView):
    """
    Base view which will handle retrieval of an object and checking permissions
    against the requesting user. The user must have 'view' permission if the
    instance is private.

    Raises
    ------
    HTTP404
    PermissionDenied
    """

    # Override the following in the inheriting view.
    # -------
    model = None
    template_name = None
    permission_required = DatasetPermissionMixin.VIEW_PERMISSION
    # -------

    context_object_name = "instance"
    http_method_names = ["get"]
    slug_url_kwarg = "urn"
    slug_field = "urn"


class CreateDatasetView(
    LoginRequiredMixin, AjaxView, DatasetFormViewContextMixin, CreateView
):
    """
    Base view for serving up multiple forms for creating a new instance.
    Handles the context creation, form handling and object creation.

    Raises
    ------
    HTTP404
    PermissionDenied
    """

    raise_exception = True
    success_url = "/profile/"
    http_method_names = ["get", "post"]

    template_name = None
    context_object_name = "instance"

    # Don't use these. Override get_form instead
    model = None
    form_class = None

    def get_permission_denied_message(self) -> str:
        return "Please log in to continue."


class UpdateDatasetView(
    DatasetPermissionMixin,
    AjaxView,
    DatasetFormViewContextMixin,
    UpdateView,
):
    """
    Base view for serving up multiple forms for updating an instance.
    Handles the context creation, form handling and object creation.

    Raises
    ------
    HTTP404
    PermissionDenied
    """

    permission_required = DatasetPermissionMixin.EDIT_PERMISSION
    raise_exception = True

    success_url = "/profile/"
    http_method_names = ["get", "post"]

    template_name = None
    context_object_name = "instance"
    slug_url_kwarg = "urn"
    slug_field = "urn"

    # Don't use these. Override get_form instead
    model = None
    form_class = None

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.processing_state == constants.processing:
            messages.error(
                self.request,
                f"{self.object.urn} is being processed and cannot be edited.",
            )
            return HttpResponseRedirect(reverse("accounts:profile"))
        return super().dispatch(request, *args, **kwargs)

    def get_permission_denied_message(self):
        urn = self.object.urn
        return f"You do not have the required permissions to edit {urn}."
