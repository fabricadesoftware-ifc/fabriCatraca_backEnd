from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import Card
from src.core.control_Id.infra.control_id_django_app.serializers import DeviceSerializer
from src.core.control_Id.infra.control_id_django_app.models import Device


class CardSerializer(serializers.ModelSerializer):
    devices = DeviceSerializer(many=True, read_only=True)
    enrollment_device_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        required=True,
        queryset=Device.objects.all(),
        help_text="Catraca que será usada para cadastro do cartão"
    )

    class Meta:
        model = Card
        fields = ['id', 'value', 'user', 'devices', 'enrollment_device_id']
        read_only_fields = ['id', 'value', 'devices']

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