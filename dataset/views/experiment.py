from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView

from accounts.permissions import PermissionTypes, assign_user_as_instance_admin

from main.utils import is_null
from main.utils.versioning import save_and_create_revision_if_tracked_changed

from ..forms.experiment import ExperimentForm, ExperimentEditForm
from ..models.experiment import Experiment
from ..models.experimentset import ExperimentSet
from ..views.scoreset import scoreset_create_view


class ExperimentDetailView(DetailView):
    """
    object in question and render a simple template for public viewing, or
    Simple class-based detail view for an `Experiment`. Will either find the
    404.

    Parameters
    ----------
    urn : `str`
        The urn of the `Experiment` to render.
    """
    model = Experiment
    template_name = 'experiment/experiment.html'
    context_object_name = "experiment"

    def dispatch(self, request, *args, **kwargs):
        try:
            experiment = self.get_object()
        except Http404:
            response = render(
                request=request,
                template_name="main/404_not_found.html"
            )
            response.status_code = 404
            return response

        has_permission = self.request.user.has_perm(
            PermissionTypes.CAN_VIEW, experiment)
        if experiment.private and not has_permission:
            response = render(
                request=request,
                template_name="main/403_forbidden.html",
                context={"instance": experiment},
            )
            response.status_code = 403
            return response
        else:
            return super(ExperimentDetailView, self).dispatch(
                request, *args, **kwargs
            )

    def get_object(self, queryset=None):
        accession = self.kwargs.get('urn', None)
        return get_object_or_404(Experiment, accession=accession)


@login_required(login_url=reverse_lazy("accounts:login"))
def experiment_create_view(request):
    """
    This view serves up the form:
        - `ExperimentForm` for the instantiation of an Experiment instnace.

    A new experiment instance will only be created if all forms pass validation
    otherwise the forms with the appropriate errors will be served back. Upon
    success, the user is redirected to the newly created experiment page.

    Parameters
    ----------
    request : `object`
        The request object that django passes into all views.
    """
    context = {}
    pks = [i.pk for i in request.user.profile.administrator_experimentsets()]
    experimentsets = ExperimentSet.objects.filter(
        pk__in=set(pks)
    ).order_by("urn")

    experiment_form = ExperimentForm()
    experiment_form.fields["experimentset"].queryset = experimentsets
    context["experiment_form"] = experiment_form

    # If you change the prefix arguments here, make sure to change them
    # in base.js as well.
    if request.method == "POST":
        # Get the new keywords/urn/target org so that we can return
        # them for list repopulation if the form has errors.
        keywords = request.POST.getlist("keywords")
        keywords = [kw for kw in keywords if not is_null(kw)]

        sra_ids = request.POST.getlist("sra_ids")
        sra_ids = [i for i in sra_ids if not is_null(sra_ids)]

        doi_ids = request.POST.getlist("doi_ids")
        doi_ids = [i for i in doi_ids if not is_null(doi_ids)]

        pubmed_ids = request.POST.getlist("pmid_ids")
        pubmed_ids = [i for i in pubmed_ids if not is_null(pubmed_ids)]

        target_organism = request.POST.getlist("target_organism")
        target_organism = [to for to in target_organism if not is_null(to)]

        experiment_form = ExperimentForm(request.POST)
        experiment_form.fields["experimentset"].queryset = experimentsets
        context["experiment_form"] = experiment_form
        context["repop_keywords"] = ','.join(keywords)
        context["repop_sra_identifiers"] = ','.join(sra_ids)
        context["repop_doi_identifiers"] = ','.join(doi_ids)
        context["repop_pubmed_identifiers"] = ','.join(pubmed_ids)
        context["repop_target_organism"] = ','.join(target_organism)

        if not experiment_form.is_valid():
            return render(
                request,
                "experiment/new_experiment.html",
                context=context
            )
        experiment = experiment_form.save(commit=True)

        # Save and update permissions. If no experimentset was selected,
        # by default a new experimentset is created with the current user
        # as it's administrator.
        user = request.user
        assign_user_as_instance_admin(user, experiment)
        experiment.created_by = user
        experiment.update_last_edit_info(user)
        save_and_create_revision_if_tracked_changed(user, experiment)

        if not request.POST['experimentset']:
            assign_user_as_instance_admin(user, experiment.experimentset)
            experiment.experimentset.created_by = user
            experiment.experimentset.update_last_edit_info(user)
            save_and_create_revision_if_tracked_changed(
                user, experiment.experimentset
            )

        return scoreset_create_view(
            request,
            came_from_new_experiment=True,
            e_accession=experiment.accession
        )
    else:
        return render(
            request,
            "experiment/new_experiment.html",
            context=context
        )