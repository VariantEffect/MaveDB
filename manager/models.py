from enum import Enum

from accounts.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Role(Enum):
    GENERAL = "GENERAL"
    POWERUSER = "POWERUSER"

    @classmethod
    def choices(cls):
        return tuple((role.name, role.value) for role in cls)


class UserRole(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='userrole'
    )
    role = models.CharField(
        max_length=255,
        default=Role.GENERAL,
        choices=Role.choices()
    )

    def __str__(self):
        return f"{self.role}"

    @property
    def is_poweruser(self):
        # So because it's an enum, this comparison is a little weird.
        # self.role is a string that looks like 'Role.POWERUSER'
        # and Role.POWERUSER is an enum value type.
        # To compare the strings, we have to use Role.POWERUSER.name or .value
        # but these evaluate to simply strings similar to 'POWERUSER'.
        # So, let's just see if one is a substring of the other.
        return Role.POWERUSER.value in self.role


@receiver(post_save, sender=User)
def create_user_userrole(sender, instance, created, **kwargs):
    if created:
        UserRole.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_userrole(sender, instance, **kwargs):
    instance.userrole.save()
