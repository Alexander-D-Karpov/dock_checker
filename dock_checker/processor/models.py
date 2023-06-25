import uuid

from django.core.validators import FileExtensionValidator
from django.db import models


class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(null=True, blank=True, max_length=500)
    ideal_title = models.CharField(null=True, blank=True, max_length=500)
    text_locations = models.JSONField(default=dict)
    uploaded = models.DateTimeField(auto_now_add=True)
    file = models.FileField(
        upload_to="uploads/",
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
    )

    class Meta:
        ordering = ("-uploaded",)


class FileImage(models.Model):
    file = models.ForeignKey("File", related_name="images", on_delete=models.CASCADE)
    order = models.IntegerField()
    image = models.ImageField(upload_to="pages/")

    class Meta:
        unique_together = ("order", "file")
        ordering = ("order",)
