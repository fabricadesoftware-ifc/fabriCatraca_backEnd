from rest_framework import serializers

from src.core.control_id.infra.control_id_django_app.models import Device, Template
from src.core.user.infra.user_django_app.models import User


class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "registration"]


class TemplateSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=User.objects.all(),
        source="user",
        required=True,
    )
    enrollment_device_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        required=False,
        allow_null=True,
        queryset=Device.objects.all(),
        help_text="Catraca usada para cadastro biometrico remoto.",
    )

    class Meta:
        model = Template
        fields = [
            "id",
            "user",
            "user_id",
            "template",
            "finger_type",
            "finger_position",
            "enrollment_device_id",
        ]
        read_only_fields = ["id", "template", "finger_type", "finger_position"]

    def create(self, validated_data):
        validated_data.pop("enrollment_device_id", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("enrollment_device_id", None)
        return super().update(instance, validated_data)
