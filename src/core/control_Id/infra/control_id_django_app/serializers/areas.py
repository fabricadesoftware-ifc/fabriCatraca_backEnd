from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import Area


class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ['id', 'name']
        read_only_fields = ['id']