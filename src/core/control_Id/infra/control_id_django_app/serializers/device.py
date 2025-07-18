from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models.device import Device

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id', 'name', 'ip', 'username', 'password', 'is_active', 'is_default']
        read_only_fields = ['id']
        extra_kwargs = {
            'password': {'write_only': True}  # Senha nunca é retornada nas respostas
        } 