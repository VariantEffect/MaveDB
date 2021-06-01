# -*- coding: UTF-8 -*-

from django.views.generic.base import RedirectView
from django.shortcuts import reverse
from django.shortcuts import Http404

from ..models import ScoreSet, ExperimentSet, Experiment


class DatasetRedirectView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        urn = kwargs["urn"]
        if ScoreSet.objects.filter(urn__iexact=urn).first() is not None:
            view = "dataset:scoreset_detail"
        elif Experiment.objects.filter(urn__iexact=urn).first() is not None:
            view = "dataset:experiment_detail"
        elif ExperimentSet.objects.filter(urn__iexact=urn).first() is not None:
            view = "dataset:experimentset_detail"
        else:
            raise Http404()
        return reverse(view, args=args, kwargs=kwargs)
