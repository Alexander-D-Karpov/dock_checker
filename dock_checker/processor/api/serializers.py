from django.urls import reverse
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from dock_checker.processor.models import File, FileImage


class TaskSerializer(serializers.Serializer):
    processed = serializers.IntegerField()
    total = serializers.IntegerField()
    features_loaded = serializers.BooleanField()
    error = serializers.BooleanField()
    error_description = serializers.CharField()


class FileImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileImage
        fields = ["order", "image"]


class FileSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField(method_name="get_status")
    file_url = serializers.SerializerMethodField(method_name="get_file_url")
    preview = serializers.SerializerMethodField(method_name="get_preview")

    @extend_schema_field(serializers.URLField)
    def get_status(self, obj):
        return reverse("api:status", kwargs={"pk": obj.id})

    @extend_schema_field(serializers.FileField)
    def get_preview(self, obj):
        if obj.images.exists():
            return obj.images.first().image.url
        return ""

    @extend_schema_field(serializers.URLField)
    def get_file_url(self, obj):
        return reverse("api:file", kwargs={"pk": obj.id})

    class Meta:
        model = File
        fields = ["name", "ideal_title", "file", "file_url", "preview", "status"]
        extra_kwargs = {
            "ideal_title": {"read_only": True},
            "status": {"read_only": True},
            "name": {"read_only": True},
            "preview": {"read_only": True},
            "file_url": {"read_only": True},
        }

    def create(self, validated_data):
        obj = File.objects.create(
            file=validated_data["file"], name=validated_data["file"].name
        )
        return obj


class FullFileSerializer(FileSerializer):
    images = FileImageSerializer(many=True)

    class Meta:
        model = File
        fields = [
            "name",
            "ideal_title",
            "file",
            "processed_file",
            "images",
            "text_locations",
        ]


class UpdateFileTitleSerializer(serializers.Serializer):
    title = serializers.CharField()
