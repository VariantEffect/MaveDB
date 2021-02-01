from enum import Enum

from accounts.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Role(Enum):
    GENERAL = "GENERAL"
    POWERUSER = "POWERUSER"

    # TODO: if we upgrade to Django 3, we won't have to do this
    @classmethod
    def choices(cls):
        return tuple((role.name, role.value) for role in cls)


class UserRole(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="userrole"
    )
    role = models.CharField(
        max_length=255, default=Role.GENERAL, choices=Role.choices()
    )

    @property
    def is_poweruser(self):
        return self.role == f"{Role.POWERUSER}"


@receiver(post_save, sender=User)
def create_user_userrole(sender, instance, created, **kwargs):
    if created:
        UserRole.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_userrole(sender, instance, **kwargs):
    instance.userrole.save()
