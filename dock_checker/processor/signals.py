from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.cache import cache

from dock_checker.processor.models import File
from .tasks import process_pdf


@receiver(pre_save, sender=File)
def file_on_create(sender, instance: File, **kwargs):
    if instance.id and not instance.text_locations:
        cache.set(f"{instance.id}-processed", 0)
        cache.set(f"{instance.id}-total", 1)
        process_pdf.apply_async(
            kwargs={"pk": instance.pk},
            countdown=1,
        )
