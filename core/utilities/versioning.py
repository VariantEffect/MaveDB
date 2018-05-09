from datetime import datetime
import reversion
from reversion.models import Version


def track_changes(user, instance):
    comments = []
    klass = instance.__class__.__name__
    versions = Version.objects.get_for_object(instance)

    if len(versions) < 1:
        comments.append("{} created first revision.".format(user))
    else:
        prev_version = versions[0] # Recent version is always first
        for field in instance.tracked_fields():
            p_field = prev_version.field_dict.get(field)
            n_field = getattr(instance, field)
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
            reversion.set_date_created(datetime.today())
            reversion.set_comment(', '.join(comments))
