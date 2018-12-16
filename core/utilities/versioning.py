import reversion
from reversion.models import Version

from core.models import TimeStampedModel

from django.db import transaction
from django.db.models import Manager
from django.utils import timezone


def track_changes(instance, user=None):
    comments = []
    klass = instance.__class__.__name__
    versions = Version.objects.get_for_object(instance)

    if len(versions) < 1:
        comments.append("{} created first revision.".format(user))
    else:
        prev_version = versions[0]  # Recent version is always first
        for field in instance.tracked_fields():
            if field == 'licence':
                p_field = prev_version.field_dict.get(
                    '{}_{}'.format(field, 'id'))
            else:
                p_field = prev_version.field_dict.get(field)

            # Only compare the ID fields of database model instances
            n_field = getattr(instance, field)
            if isinstance(n_field, Manager):
                n_field = [i.id for i in n_field.all()]
            elif isinstance(n_field, TimeStampedModel):
                n_field = n_field.id

            # Sort the id lists to compare them if applicable
            # (for ManyToMany fields)
            if isinstance(p_field, (list, set, tuple)):
                p_field = sorted(p_field)
            if isinstance(n_field, (list, set, tuple)):
                n_field = sorted(n_field)

            if p_field != n_field:
                comments.append(
                    "{} edited {} field {}".format(user, klass, field))

    if not comments:
        instance.save()
    else:
        with reversion.create_revision():
            instance.save()
            reversion.set_user(user)
            reversion.set_date_created(timezone.now())
            reversion.set_comment(', '.join(comments))


@transaction.atomic
def revert(instance):
    """
    Rollsback fields to the last version

    Using previous_version.revision.revert() will throw a RevertError
    """
    versions = Version.objects.get_for_object(instance)
    if versions.count():
        previous_version = versions[0]
        for field in instance.tracked_fields():
            previous_field_value = previous_version.field_dict.get(field)
            current_field_value = getattr(instance, field)
            if isinstance(previous_field_value, (set, list, tuple)):
                current_field_value.clear()
                for pk in previous_field_value:
                    current_field_value.add(pk)
            else:
                setattr(instance, field, previous_field_value)

        with reversion.create_revision():
            reversion.set_date_created(timezone.now())
            reversion.set_comment(
                "Reverted to revision Version instance with id {} "
                "created on {} by user {}.".format(
                    previous_version.revision.id,
                    previous_version.revision.date_created,
                    previous_version.revision.user
                )
            )
            instance.save()

    instance.refresh_from_db()
    return instance
