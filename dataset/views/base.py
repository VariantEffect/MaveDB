from braces.views import (
    PermissionRequiredMixin, UserFormKwargsMixin, LoginRequiredMixin
)

from django.views.generic import DetailView, FormView, UpdateView
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from ..models.base import DatasetModel


class DatasetModelView(DetailView, PermissionRequiredMixin):
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
    # The following MUST be overriden in the inheriting view.
    model = DatasetModel
    template_name = None
    raise_exception = True
    permission_required = None

    context_object_name = "instance"
    http_method_names = ['get']
    login_url = "/login/"

    def get_object(self, queryset=None):
        urn = self.kwargs.get('urn', None)
        return get_object_or_404(self.model, urn=urn)

    def check_permissions(self, request=None):
        instance = self.get_object()
        has_permission = super().check_permissions(request) and instance.private
        return has_permission

    def handle_no_permission(self, request):
        try:
            return super().handle_no_permission(request)
        except PermissionDenied:
            instance = self.get_object()
            raise PermissionDenied(
                "{urn} is a private entry and is under restricted access until "
                "it is published.".format(
                    urn=instance.urn
                )
            )



class CreateDatasetModelView(UserFormKwargsMixin, FormView, LoginRequiredMixin):
    pass



class UpdateDatasetModelView(UserFormKwargsMixin, UpdateView,
                             PermissionRequiredMixin):
    pass