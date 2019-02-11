# -*- coding: UTF-8 -*-

from .base import DatasetModelView
from ..models.experimentset import ExperimentSet


class ExperimentSetDetailView(DatasetModelView):
    """
    Simple class-based detail view for an `ExperimentSet`. Will either find the
    object in question and render a simple template for public viewing, or
    404.

    Parameters
    ----------
    urn : `str`
        The urn of the `ExperimentSet` to render.
    """
    # Overriding from `DatasetModelView`.
    # -------
    model = ExperimentSet
    template_name = 'dataset/experimentset/experimentset.html'
    # -------
