from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import Device

class DeviceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Device
        fields = ['id', 'name', 'ip', 'username', 'password', 'is_active', 'is_default']
        extra_kwargs = {
            'password': {'write_only': True}  # Senha nunca é retornada nas respostas
        } 

    def validate_id(self, value):
        if value in (None, ''):
            return None
        if int(value) <= 0:
            raise serializers.ValidationError("O ID da catraca deve ser maior que zero.")
        return int(value)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = getattr(self, "instance", None)
        if instance and "id" in attrs and attrs["id"] != instance.id:
            raise serializers.ValidationError(
                {"id": ["O ID da catraca não pode ser alterado após o cadastro."]}
            )
        return attrs