from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import TimeZone

class TimeZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeZone
        fields = ['id', 'name']
        read_only_fields = ['id']