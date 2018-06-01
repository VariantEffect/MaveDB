from django.contrib import messages
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist

from main.context_processors import baseurl

from accounts.permissions import PermissionTypes

from dataset import constants
from dataset.models.experimentset import ExperimentSet
from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet
from dataset.tasks import publish_scoreset
from dataset.utilities import delete_instance

from urn.models import get_model_by_urn


def delete(urn, request):
    """
    Validates a request to delete an instance. Checks:
        - urn exists
        - requesting user has permission
        - Does not have children (experiments and experimentsets only)
        - is not being processed by celery
        - does not have children being processed
    """
    try:
        instance = get_model_by_urn(urn=urn)
        if not request.user.has_perm(
                PermissionTypes.CAN_MANAGE, instance):
            raise PermissionDenied()
    except ObjectDoesNotExist:
        messages.error(request, "{} has already been deleted.".format(urn))
        return False
    except PermissionDenied:
        messages.error(
            request, "You must be an administrator for {} to delete "
                     "it.".format(urn))
        return False

    # Check doesn't have children if experiment or experimentset
    if isinstance(instance, (Experiment, ExperimentSet)):
        if instance.children.count():
            message = (
                "Child {child_class}s must be deleted prior "
                "to deleting this {parent_class}."
            ).format(
                child_class=instance.children.first().__class__.__name__,
                parent_class=instance.__class__.__name__,
            )
            messages.error(request, message)
            return False

    # Check the processing state
    being_processed = instance.processing_state == constants.processing
    if being_processed:
        messages.error(
            request,
            "{} cannot be deleted because it is currently being "
            "processed. Try again once your submission has "
            "been processed.".format(instance.urn))
        return False

    # Check the private status
    if instance.private:
        delete_instance(instance)
        messages.success(
            request, "Successfully deleted {}.".format(urn))
        return True
    else:
        messages.error(
            request, "{} is public and cannot be deleted.".format(instance.urn))
        return False


def publish(urn, request):
    """
    Validates a request to publish a scoreset. Checks:
        - urn exists and is a score set
        - requesting user has permission
        - is not being processed by celery
        - has variants that are associated
        - is not in the 'failed' celery state
        - has not been published already
    """
    try:
        instance = get_model_by_urn(urn=urn)
        if not request.user.has_perm(
                PermissionTypes.CAN_MANAGE, instance):
            raise PermissionDenied()
    except ObjectDoesNotExist:
        messages.error(request, "Could not find {}. It may have been "
                                "deleted.".format(urn))
        return False
    except PermissionDenied:
        messages.error(
            request, "You must be an administrator for {} to publish "
                     "it.".format(urn))
        return False
    
    if not isinstance(instance, ScoreSet):
        messages.error(request, "Only Score Sets can be published.".format(urn))
        return False
  
    # Check the processing state
    being_processed = instance.processing_state == constants.processing
    if being_processed:
        messages.error(
            request,
            "{} cannot be publish because it is currently being "
            "processed. Try again once your processing has completed.".format(
                urn))
        return False
    
    # check if in fail state
    failed = instance.processing_state == constants.failed
    if failed:
        messages.error(
            request,
            "{} cannot be publish because there were errors during "
            "the previous submission attempt. You will need to complete your "
            "submission before publishing.".format(urn))
        return False
    
    # Check if has variants
    has_variants = instance.has_variants
    if not has_variants:
        messages.error(
            request,
            "{} cannot be publish because there are no associated variants. "
            "You will need to complete your submission before "
            "publishing.".format(urn))
        return False
    
    # Check the private status
    if instance.private:
        instance.processing_state = constants.processing
        instance.save()
        publish_scoreset.delay(
            scoreset_urn=instance.urn,
            user_pk=request.user.pk,
            base_url=baseurl(request)['BASE_URL'],
        )
        messages.success(
            request,
            "{} has been queued for publication. Editing has been "
            "disabled until your submission has been processed. A public urn "
            "will be assigned upon successful completion.".format(urn))
        return True
    else:
        messages.error(
            request, "{} is public and cannot be published again.".format(urn))
        return False