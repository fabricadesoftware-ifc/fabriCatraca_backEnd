from rest_framework import serializers
from core.uploader.models import Archive


class ArchiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Archive
        fields = ["id", "titulo", "arquivo", "criado_em"]
        read_only_fields = ["id", "criado_em"]
