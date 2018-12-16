import sys
from django.core.management.base import BaseCommand

from dataset import constants
from urn.models import get_model_by_urn


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--state', type=str, help="Processing state",)
        parser.add_argument(
            '--urn', type=str, help="Dataset URN",)

    def handle(self, *args, **kwargs):
        state = kwargs.get('state', None)
        if state not in (constants.processing, constants.failed, constants.success):
            raise ValueError("Valid states are {}, {} or {}.".format(
                constants.processing, constants.failed, constants.success
            ))
        
        urn = kwargs.get('urn', None)
        if not urn:
            raise ValueError("A valid URN is required.")

        instance = get_model_by_urn(urn)
        instance.processing_state = state
        instance.save()
        sys.stderr.write("Set {} state to {}.\n".format(instance, state))
