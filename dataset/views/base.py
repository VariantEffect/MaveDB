from django.views.generic import DetailView

from ..models.base import DatasetModel

class DatasetModelDetailView(DetailView):

    # These must be set by the inheriting class.
    model = None
    template_name = None
    context_object_name = 'instance'

