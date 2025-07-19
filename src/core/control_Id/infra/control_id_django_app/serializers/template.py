from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import Template
from src.core.control_Id.infra.control_id_django_app.serializers import DeviceSerializer
from src.core.control_Id.infra.control_id_django_app.models import Device

class TemplateSerializer(serializers.ModelSerializer):
    devices = DeviceSerializer(many=True, read_only=True)
    enrollment_device_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        required=True,
        queryset=Device.objects.all(),
        help_text="Catraca que será usada para cadastro biométrico"
    )

    class Meta:
        model = Template
        fields = ['id', 'user', 'template', 'finger_type', 'finger_position', 'devices', 'enrollment_device_id']
        read_only_fields = ['id', 'template', 'finger_type', 'finger_position', 'devices']

    def create(self, validated_data):
        devices = validated_data.pop('devices', [])
        validated_data.pop('enrollment_device_id', None)  # Removemos pois não salvamos
        instance = super().create(validated_data)
        if devices:
            instance.devices.set(devices)
        return instance

    def update(self, instance, validated_data):
        devices = validated_data.pop('devices', None)
        validated_data.pop('enrollment_device_id', None)  # Removemos pois não salvamos
        instance = super().update(instance, validated_data)
        if devices is not None:  # Atualiza apenas se foi fornecido
            instance.devices.set(devices)
        return instance