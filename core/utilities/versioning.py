
import reversion
from reversion.models import Version


def track_changes(user, instance):
    comments = []
    klass = instance.__class__.__name__
    versions = Version.objects.get_for_object(instance)

    # Store these to check if uneeded revisions are added later.
    if klass == "ScoreSet":
        experiment = instance.experiment
        experimentset = experiment.experimentset
        old_exp_versions = Version.objects.get_for_object(experiment)
        old_exps_versions = Version.objects.get_for_object(
            experimentset
        )

    if len(versions) < 1:
        comments.append("{} created first revision.".format(user))
    else:
        prev_version = versions[0]
        for field in instance.TRACKED_FIELDS:
            p_field = prev_version.field_dict.get(field)
            n_field = getattr(instance, field)
            if field in ("keywords", "external_accessions"):
                p_field = sorted(p_field)
                n_field = sorted([o.pk for o in n_field.all()])
            if p_field != n_field:
                comments.append(
                    "{} edited {} field {}".format(user, klass, field))

    if not comments:
        instance.save()
    else:
        with reversion.create_revision():
            instance.save()
            reversion.set_user(user)
            reversion.set_comment(', '.join(comments))

    # Delete revisions created in a post_save signal from ScoreSet that
    # don't involve the private/approved bit being changed.
    if klass == "ScoreSet" and not any(["private" in c for c in comments]) \
            and not any(["approved" in c for c in comments]):
        new_exp_versions = Version.objects.get_for_object(experiment)
        new_exps_versions = Version.objects.get_for_object(experimentset)

        if len(old_exp_versions) < len(new_exp_versions):
            Version.objects.get_for_object(experiment)[0].delete()

        if len(old_exps_versions) < len(new_exps_versions):
            Version.objects.get_for_object(experimentset)[0].delete()
