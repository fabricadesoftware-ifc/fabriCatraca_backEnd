from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import Template, Device
from src.core.user.infra.user_django_app.models import User


class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "registration"]


class TemplateSerializer(serializers.ModelSerializer):
    # ✅ Saída: retorna dados básicos do usuário
    user = UserBasicSerializer(read_only=True)

    # ✅ Entrada: aceita só o id do usuário
    user_id = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=User.objects.all(), source="user", required=True
    )

    enrollment_device_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        required=False,
        allow_null=True,
        queryset=Device.objects.all(),
        help_text="Catraca que será usada para cadastro biométrico",
    )

    enrollment_mode = serializers.ChoiceField(
        write_only=True,
        required=False,
        choices=["remote", "local"],
        default="remote",
        help_text="Modo de cadastro biométrico: remote (catraca) ou local (SDK USB).",
    )

    captured_template = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        help_text="Template biométrico capturado localmente (modo local).",
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
            "enrollment_mode",
            "captured_template",
        ]
        read_only_fields = ["id", "template", "finger_type", "finger_position"]

    def create(self, validated_data):
        validated_data.pop("enrollment_device_id", None)
        validated_data.pop("enrollment_mode", None)
        validated_data.pop("captured_template", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("enrollment_device_id", None)
        validated_data.pop("enrollment_mode", None)
        validated_data.pop("captured_template", None)
        return super().update(instance, validated_data)
