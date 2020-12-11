from django.contrib import messages
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist

from accounts.permissions import PermissionTypes

from dataset import constants
from dataset.models.experimentset import ExperimentSet
from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet
from dataset.tasks import publish_scoreset, delete_instance

from urn.models import get_model_by_urn


def delete(urn, request):
    """
    Validates a request to delete an instance. Checks:
        - urn exists
        - requesting user has permission
        - Does not have children (experiments and experimentsets only)
        - is not being processed by celery
        - does not have children being processed
        - Cascade deletes meta-analysis parents if only score set is being
          deleted
    """
    try:
        instance = get_model_by_urn(urn=urn)
        if not request.user.has_perm(PermissionTypes.CAN_MANAGE, instance):
            raise PermissionDenied()
    except ObjectDoesNotExist:
        messages.error(request, f"{urn} has already been deleted.")
        return False
    except PermissionDenied:
        messages.error(
            request, f"You must be an administrator for {urn} to delete it."
        )
        return False

    # Check doesn't have children if experiment or experimentset
    if isinstance(instance, (Experiment, ExperimentSet)):
        if instance.children.count():
            message = (
                "Child {child_class}s must be deleted prior "
                "to deleting this {parent_class}."
            ).format(
                child_class=instance.children.first()
                .__class__.__name__.replace("Set", " set")
                .lower(),
                parent_class=instance.__class__.__name__.replace(
                    "Set", " set"
                ).lower(),
            )
            messages.error(request, message)
            return False

    # Check the processing state
    being_processed = instance.processing_state == constants.processing
    if being_processed:
        messages.error(
            request,
            f"{instance.urn} cannot be deleted because it is currently being "
            "processed. Try again once your submission has "
            "been processed.",
        )
        return False

    # Check the private status
    if instance.private:
        current_state = instance.processing_state
        instance.processing_state = constants.processing
        instance.save()
        task_kwargs = dict(urn=instance.urn, user_pk=request.user.pk)
        success, _ = delete_instance.submit_task(
            kwargs=task_kwargs, request=request
        )
        if success:
            messages.success(
                request,
                f"{urn} has been queued for deletion. Editing has been "
                "disabled until your submission has been processed.",
            )
            return True
        else:
            instance.processing_state = current_state
            instance.save()
            messages.error(
                request,
                "We are experiencing server issues at the moment. Please try"
                "again later.",
            )
            return False
    else:
        messages.error(
            request, f"{instance.urn} is public and cannot be deleted."
        )
        return False


def publish(urn, request):
    """
    Validates a request to publish a scoreset. Checks:
        - urn exists and is a score set
        - requesting user has permission
        - is not being processed by celery
        - dataset has variants that are associated and is not empty
        - is not in the 'failed' celery state
        - has not been published already
        - Use has permission to publish the whole parent tree (
          has manage permissions)
    """

    try:
        instance = get_model_by_urn(urn=urn)  # type: ScoreSet
        if not request.user.has_perm(PermissionTypes.CAN_MANAGE, instance):
            raise PermissionDenied(
                f"You must be an administrator for {instance.urn} to "
                f"publish it."
            )

        if not isinstance(instance, ScoreSet):
            messages.error(request, "Only score sets can be published.")
            return False

        experiment = instance.experiment
        experimentset = instance.experiment.experimentset
        admin_for_exp_set = request.user.has_perm(
            PermissionTypes.CAN_MANAGE, experimentset
        )
        admin_for_exp = request.user.has_perm(
            PermissionTypes.CAN_MANAGE, experiment
        )
        if instance.is_meta_analysis:
            if experimentset.private and experimentset.is_mixed_meta_analysis:
                # This shouldn't happen because a meta-analysis can only be
                # linked to a published score set, meaning the experiment set
                # will always be public.
                if not admin_for_exp_set:
                    raise PermissionDenied(
                        f"You must be an administrator for experiment set "
                        f"{experimentset.urn} before being able to "
                        f"publish {instance.urn}."
                    )
        else:
            if experiment.private and not admin_for_exp:
                raise PermissionDenied(
                    f"You must be an administrator for experiment "
                    f"{experiment.urn} before being able to "
                    f"publish {instance.urn}."
                )
            if experiment.private and not admin_for_exp_set:
                raise PermissionDenied(
                    f"You must be an administrator for experiment set "
                    f"{experimentset.urn} before being able to "
                    f"publish {instance.urn}."
                )
    except ObjectDoesNotExist:
        messages.error(
            request,
            f"Could not find {urn}. It may have been deleted.",
        )
        return False
    except PermissionDenied as error:
        messages.error(request, str(error))
        return False

    # Check the processing state
    being_processed = instance.processing_state == constants.processing
    if being_processed:
        messages.error(
            request,
            "{} cannot be publish because it is currently being "
            "processed. Try again once processing has completed.".format(urn),
        )
        return False

    # check if in fail state
    failed = instance.processing_state == constants.failed
    if failed:
        messages.error(
            request,
            "{} cannot be publish because there were errors during "
            "the previous submission attempt. You will need to complete your "
            "submission before publishing.".format(urn),
        )
        return False

    # Check if has variants
    has_variants = instance.has_variants
    if not has_variants:
        messages.error(
            request,
            "{} cannot be publish because there are no associated variants. "
            "You will need to complete your submission before "
            "publishing.".format(urn),
        )
        return False

    # Check the private status
    if instance.private:
        current_state = instance.processing_state
        instance.processing_state = constants.processing
        instance.save()
        task_kwargs = dict(scoreset_urn=instance.urn, user_pk=request.user.pk)
        success, _ = publish_scoreset.submit_task(
            kwargs=task_kwargs, request=request
        )
        if success:
            messages.success(
                request,
                "{} has been queued for publication. Editing has been disabled "
                "until your submission has been processed. A public urn "
                "will be assigned upon successful completion.".format(urn),
            )
            return True
        else:
            instance.processing_state = current_state
            instance.save()
            messages.error(
                request,
                "We are experiencing server issues at the moment. Please try"
                "again later.",
            )
            return False
    else:
        messages.error(
            request, "{} is public and cannot be published again.".format(urn)
        )
        return False
