import logging

from django.views.generic import DetailView, FormView
from django.contrib.auth.mixins import (
    LoginRequiredMixin
)
from django.shortcuts import reverse
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect

from dataset import constants
from dataset.mixins import DatasetUrnMixin, DatasetPermissionMixin, \
    DatasetFormViewContextMixin, MultiFormMixin

from ..forms.base import DatasetModelForm
from ..models.base import DatasetModel


logger = logging.getLogger("django")


class DatasetModelView(DatasetPermissionMixin, DatasetUrnMixin, DetailView):
    """
    Base view which will handle retrieval of an object and checking permissions
    against the requesting user. The user must have 'view' permission if the
    instance is private.

    Parameters
    ----------
    urn : str
        The urn to display

    Raises
    ------
    HTTP404
    PermissionDenied
    """
    # Override the following in the inheriting view.
    # -------
    model = DatasetModel
    template_name = None
    # -------

    context_object_name = "instance"
    http_method_names = ['get']
    login_url = "/login/"


class DatasetModelFormView(DatasetFormViewContextMixin,
                           FormView,
                           MultiFormMixin):
    # Override the following in the inheriting view.
    # -------
    form_class = DatasetModelForm  # Unused but defined for Django compliance.
    template_name = None
    model_class_name = 'dataset'
    # -------

    success_url = '/profile/'
    prefix = None
    success_message = None

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            return self.get_ajax(request, *args, **kwargs)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.is_ajax():
            return self.post_ajax(request, *args, **kwargs)
        all_valid, forms = self.forms_valid()
        if not all_valid:
            return self.form_invalid(forms)
        else:
            return self.form_valid(forms)

    def get_ajax(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def post_ajax(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_form(self, form_class=None):
        # Pass this. We're using `get_forms` from MultiFormMixin.
        return None

    def form_invalid(self, forms):
        """
        Overridden from FormView. We just redirect to the same url if invalid.
        We're just changing `form` to `forms` to add the forms with errors to
        the context.
        """
        return self.render_to_response(self.get_context_data(**forms))

    def form_valid(self, forms=None):
        """
        Overridden from FormView. FormView definition just redirects to
        success url or back to the same url if invalid. We're just adding some
        extra logic on top to handle all the additional forms.
        """
        try:
            forms = self.save_forms(forms)
            message = self.format_success_message()
            if message:
                messages.success(self.request, message)
            return super().form_valid(forms)
        except Exception as e:
            logger.exception(
                "The following error occured during "
                "{} creation:\n{}".format(self.model_class_name, str(e))
            )
            messages.error(
                self.request,
                "There was a server side error while saving your submission "
                "Try again or contact us if this issue persists."
            )
            return self.form_invalid(forms)

    def format_success_message(self):
        return None


class CreateDatasetModelView(LoginRequiredMixin, DatasetModelFormView):
    """
    Base view for serving up multiple forms for creating a new instance.
    Handles the context creation, form handling and object creation.

    Raises
    ------
    HTTP404
    """
    login_url = '/login/'
    success_message = (
        "Successfully created a new {model_name}, which has been assigned a "
        "temporary accession number {urn}."
    )

    def format_success_message(self):
        return self.success_message.format(
            model_name=self.model_class_name, urn=self.kwargs.get('urn', None)
        )


class UpdateDatasetModelView(DatasetPermissionMixin,
                             DatasetUrnMixin,
                             DatasetModelFormView):
    """
    Base view for serving up multiple forms for updating an instance.
    Handles the context creation, form handling and object creation.

    Raises
    ------
    HTTP404
    PermissionDenied
    """

    success_message = "Successfully updated {urn}."
    permission_required = 'dataset.can_edit'
    model_class = None
    permission_denied_message = \
        'You do not have the required permissions to edit {urn}.'

    def dispatch(self, request, *args, **kwargs):
        try:
            self.instance = self.get_object()
            if self.instance.processing_state == constants.processing:
                messages.error(
                    request,
                    "{} is being processed and cannot be edited.".format(
                        self.instance.urn)
                )
                return HttpResponseRedirect(reverse("accounts:profile"))
            return super().dispatch(request, *args, **kwargs)
        except PermissionDenied:
            urn = self.kwargs.get('urn', None)
            messages.error(
                self.request,
                self.permission_denied_message.format(urn=urn)
            )
            return HttpResponseRedirect(reverse("accounts:profile"))

    def format_success_message(self):
        return self.success_message.format(urn=self.instance.urn)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['instance'] = self.instance
        return context
    
    def form_invalid(self, forms):
        messages.error(self.request, "Your submission contains errors.")
        return super(UpdateDatasetModelView, self).form_invalid(forms)
