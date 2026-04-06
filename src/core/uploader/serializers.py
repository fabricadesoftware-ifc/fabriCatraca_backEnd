from rest_framework import serializers
from src.core.uploader.models import Archive


class ArchiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Archive
        fields = ["id", "titulo", "arquivo", "created_at"]
        read_only_fields = ["id", "created_at"]
