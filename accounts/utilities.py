import logging

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.shortcuts import reverse

from dataset import models


logger = logging.getLogger('django')


def notify_user(base_url, user, instance, action, group):
    if not hasattr(instance, 'urn'):
        logger.error(
            "{} passed to accounts.utilities.notify_user "
            "has no attribute urn".format(type(instance).__name__)
        )
        return

    if isinstance(instance, models.experiment.Experiment):
        path = reverse("dataset:experiment_detail", args=(instance.urn,))
    elif isinstance(instance, models.scoreset.ScoreSet):
        path = reverse("dataset:scoreset_detail", args=(instance.urn,))
    elif isinstance(instance, models.experimentset.ExperimentSet):
        path = reverse("dataset:experimentset_detail", args=(instance.urn,))
    else:
        logger.error(
            "{} passed to accounts.utlitiles.notify_user "
            "is not a valid viewable instance.".format(type(instance).__name__)
        )
        return

    if isinstance(base_url, dict):
        base_url = base_url['BASE_URL']
    if isinstance(base_url, str):
        absolute_url = base_url + path
    else:
        logger.error("Unkown base_url type '{}'".format(
            type(base_url).__name__))
        return

    email = user.profile.email or user.email
    if action == 'removed':
        conjunction = 'from'
    else:
        conjunction = 'for'

    if group in ('administrator', 'editor'):
        group = 'an {}'.format(group)
    else:
        group = 'a {}'.format(group)

    if email:
        template_name = "accounts/added_removed_as_contributor.html"
        message = render_to_string(template_name, {
            'user': user, 'group': group, 'conjunction': conjunction,
            'url': absolute_url, 'action': action, 'urn': instance.urn
        })
        send_mail(
            subject='Updates to entry {}.'.format(instance.urn),
            message=message,
            from_email=None,
            recipient_list=[email]
        )
    else:
        logger.error(
            "Tried to notify user '{}' from accounts.utilities.notify_user "
            "but could not find an email address.".format(user.username)
        )
