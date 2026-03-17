from rest_framework import serializers

from ..models import SecurityConfig


class SecurityConfigSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)

    # Campos legados mantidos por compatibilidade.
    password_only = serializers.BooleanField(required=False, default=False)
    hide_password_only = serializers.BooleanField(required=False, default=False)
    hide_name_on_identification = serializers.BooleanField(required=False, default=False)
    send_code_when_not_identified = serializers.BooleanField(required=False, default=False)
    send_code_when_not_authorized = serializers.BooleanField(required=False, default=False)

    # Campos realmente enviados ao bloco `identifier`.
    verbose_logging = serializers.BooleanField(
        source="verbose_logging_enabled",
        required=False,
        default=True,
    )
    log_type = serializers.IntegerField(required=False, default=1, min_value=0, max_value=2)
    multi_factor_authentication = serializers.BooleanField(
        source="multi_factor_authentication_enabled",
        required=False,
        default=False,
    )

    class Meta:
        model = SecurityConfig
        fields = [
            "id",
            "device",
            "device_name",
            "password_only",
            "hide_password_only",
            "password_only_tip",
            "hide_name_on_identification",
            "denied_transaction_code",
            "send_code_when_not_identified",
            "send_code_when_not_authorized",
            "verbose_logging",
            "log_type",
            "multi_factor_authentication",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "device": {"required": False},
            "password_only_tip": {"required": False},
            "denied_transaction_code": {"required": False},
        }

    def validate_denied_transaction_code(self, value):
        if value in (None, "", "0", 0):
            return ""

        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError as exc:
                raise serializers.ValidationError("Codigo deve ser um numero inteiro") from exc

        if not (1 <= value <= 999):
            raise serializers.ValidationError("Codigo deve estar entre 1 e 999")

        return value

    def to_internal_value(self, data):
        if hasattr(data, "_mutable"):
            data = data.copy()
        elif not isinstance(data, dict):
            data = dict(data)

        boolean_fields = {
            "password_only": False,
            "hide_password_only": False,
            "hide_name_on_identification": False,
            "send_code_when_not_identified": False,
            "send_code_when_not_authorized": False,
            "verbose_logging": True,
            "multi_factor_authentication": False,
        }

        if self.partial:
            for field, default_value in boolean_fields.items():
                if field not in data:
                    data[field] = default_value

        return super().to_internal_value(data)
