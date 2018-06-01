import logging

from django.http import HttpRequest
from django.urls import reverse_lazy
from django.db import transaction

from core.tasks import email_admins
from core.utilities.versioning import track_changes

from ..forms.experiment import ExperimentForm, ExperimentEditForm
from ..models.experiment import Experiment

from .base import (
    DatasetModelView, CreateDatasetModelView, UpdateDatasetModelView
)

logger = logging.getLogger("django")


class ExperimentDetailView(DatasetModelView):
    """
    object in question and render a simple template for public viewing, or
    Simple class-based detail view for an `Experiment`. Will either find the
    404.

    Parameters
    ----------
    urn : :class:`HttpRequest`
        The urn of the `Experiment` to render.
    """
    # Overriding from `DatasetModelView`.
    # -------
    model = Experiment
    template_name = 'dataset/experiment/experiment.html'
    # -------

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = self.get_object()
        keywords = set([kw for kw in instance.keywords.all()])
        keywords = sorted(
            keywords, key=lambda kw: -1 * kw.get_association_count())
        context['keywords'] = keywords
        return context


class ExperimentCreateView(CreateDatasetModelView):
    """
    This view serves up the form:
        - `ExperimentForm` for the instantiation of an Experiment instnace.

    A new experiment instance will only be created if all forms pass validation
    otherwise the forms with the appropriate errors will be served back. Upon
    success, the user is redirected to the newly created experiment page.

    Parameters
    ----------
    request : :class:`HttpRequest`
        The request object that django passes into all views.
    """
    # Overridden from `CreateDatasetModelView`
    # -------
    form_class = ExperimentForm
    template_name = 'dataset/experiment/new_experiment.html'
    model_class_name = 'Experiment'
    # -------

    forms = {"experiment": ExperimentForm}

    @transaction.atomic
    def save_forms(self, forms):
        experiment_form = forms['experiment']
        experiment = experiment_form.save(commit=True)
        # Save and update permissions. If no experimentset was selected,
        # by default a new experimentset is created with the current user
        # as it's administrator.
        experiment.add_administrators(self.request.user)
        experiment.set_created_by(self.request.user, propagate=False)
        experiment.set_modified_by(self.request.user, propagate=False)
        experiment.save(save_parents=False)
        
        if not self.request.POST['experimentset']:
            experiment.experimentset.add_administrators(self.request.user)
            email_admins.delay(self.request.user.pk,
                               experiment.experimentset.urn)
            propagate = True
            save_parents = True
        else:
            propagate = False
            save_parents = False

        experiment.set_created_by(self.request.user, propagate=propagate)
        experiment.set_modified_by(self.request.user, propagate=propagate)
        experiment.save(save_parents=save_parents)
        track_changes(instance=experiment, user=self.request.user)
        track_changes(instance=experiment.parent, user=self.request.user)
        self.kwargs['urn'] = experiment.urn
        return forms

    def get_experiment_form_kwargs(self, key):
        return {'user': self.request.user}

    def get_success_url(self):
        return "{}{}".format(
            reverse_lazy("dataset:scoreset_new"),
            "?experiment={}".format(self.kwargs['urn'])
        )


class ExperimentEditView(UpdateDatasetModelView):
    """
    This view serves up the form:
        - `ExperimentForm` for the instantiation of an Experiment instnace.

    A new experiment instance will only be created if all forms pass validation
    otherwise the forms with the appropriate errors will be served back. Upon
    success, the user is redirected to the newly created experiment page.

    Parameters
    ----------
    request : :class:`HttpRequest`
        The request object that django passes into all views.
    """
    # Overridden from `CreateDatasetModelView`
    # -------
    form_class = ExperimentForm
    template_name = 'dataset/experiment/update_experiment.html'
    model_class_name = 'Experiment'
    model_class = Experiment
    # -------

    forms = {"experiment": ExperimentForm}
    restricted_forms = {"experiment": ExperimentEditForm}

    @transaction.atomic
    def save_forms(self, forms):
        experiment_form = forms['experiment']
        experiment = experiment_form.save(commit=True)
        experiment.set_modified_by(self.request.user, propagate=False)
        track_changes(instance=experiment, user=self.request.user)
        self.kwargs['urn'] = experiment.urn
        return forms

    def get_experiment_form(self, form_class, **form_kwargs):
        if self.request.method == "POST":
            if self.instance.private:
                return ExperimentForm.from_request(
                    self.request, self.instance, initial=None,
                    prefix=self.prefixes.get('experiment', None)
                )
            else:
                return ExperimentEditForm.from_request(
                    self.request, self.instance, initial=None,
                    prefix=self.prefixes.get('experiment', None)
                )
        else:
            if 'user' not in form_kwargs:
                form_kwargs.update({'user': self.request.user})
            return form_class(**form_kwargs)
