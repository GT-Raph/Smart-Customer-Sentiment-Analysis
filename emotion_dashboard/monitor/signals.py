from django.db.models.signals import (
    post_save,
)
from django.dispatch import receiver

from .models import (
    CustomUser,
    UserPreference,
)


@receiver(
    post_save,
    sender=CustomUser,
)
def create_user_preferences(
    sender,
    instance,
    created,
    **kwargs,
):
    if created:
        UserPreference.objects.get_or_create(
            user=instance
        )