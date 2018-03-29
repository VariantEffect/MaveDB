from django.http import Http404
from django.shortcuts import render, get_object_or_404
from django.views.generic import DetailView

from accounts.permissions import PermissionTypes

from ..models.experimentset import ExperimentSet


class ExperimentSetDetailView(DetailView):
    """
    Simple class-based detail view for an `ExperimentSet`. Will either find the
    object in question and render a simple template for public viewing, or
    404.

    Parameters
    ----------
    urn : `str`
        The urn of the `ExperimentSet` to render.
    """
    model = ExperimentSet
    template_name = 'experiment/experimentset.html'
    context_object_name = "experimentset"

    def dispatch(self, request, *args, **kwargs):
        try:
            experimentset = self.get_object()
        except Http404:
            response = render(
                request=request,
                template_name="main/404_not_found.html"
            )
            response.status_code = 404
            return response

        has_permission = self.request.user.has_perm(
            PermissionTypes.CAN_VIEW, experimentset)
        if experimentset.private and not has_permission:
            response = render(
                request=request,
                template_name="main/403_forbidden.html",
                context={"instance": experimentset},
            )
            response.status_code = 403
            return response
        else:
            return super(ExperimentSetDetailView, self).dispatch(
                request, *args, **kwargs
            )

    def get_object(self, queryset=None):
        accession = self.kwargs.get('urn', None)
        return get_object_or_404(ExperimentSet, accession=accession)