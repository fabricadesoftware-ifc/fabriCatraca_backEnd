from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import Portal

class PortalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portal
        fields = ['id', 'name', 'area_from_id', 'area_to_id'] 
        read_only_fields = ['id']