from rest_framework import serializers
from ..models import SystemConfig


class SystemConfigSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)

    # CORREÇÃO: Campos booleanos explícitos para corrigir comportamento do HTML form do DRF
    # Quando checkbox está desmarcado, HTML form não envia nada
    # required=False permite campo ausente, default=False interpreta ausência como False
    clear_expired_users = serializers.BooleanField(required=False, default=False)
    url_reboot_enabled = serializers.BooleanField(required=False, default=True)
    keep_user_image = serializers.BooleanField(required=False, default=True)
    online = serializers.BooleanField(required=False, default=True)
    local_identification = serializers.BooleanField(required=False, default=True)
    web_server_enabled = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = SystemConfig
        fields = [
            "id",
            "device",
            "device_name",
            "auto_reboot_hour",
            "auto_reboot_minute",
            "clear_expired_users",
            "url_reboot_enabled",
            "keep_user_image",
            "catra_timeout",
            "online",
            "local_identification",
            "language",
            "daylight_savings_time_start",
            "daylight_savings_time_end",
            "web_server_enabled",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            'device': {'required': False},  # Não obrigatório em updates
            'auto_reboot_hour': {'required': False},
            'auto_reboot_minute': {'required': False},
            'catra_timeout': {'required': False},
            'language': {'required': False},
            'daylight_savings_time_start': {'required': False},
            'daylight_savings_time_end': {'required': False}
        }

    def validate_auto_reboot_hour(self, value):
        # Aceita None ou string vazia como válidos (campo opcional)
        if value is None or value == '':
            return value
        
        # Converte para int se for string (vem do HTML form)
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                raise serializers.ValidationError("Hora deve ser um número inteiro")
        
        # Valida o range numérico
        if not (0 <= value <= 23):
            raise serializers.ValidationError("Hora deve estar entre 0 e 23")
        
        return value

    def validate_auto_reboot_minute(self, value):
        # Aceita None ou string vazia como válidos (campo opcional)
        if value is None or value == '':
            return value
        
        # Converte para int se for string (vem do HTML form)
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                raise serializers.ValidationError("Minuto deve ser um número inteiro")
        
        # Valida o range numérico
        if not (0 <= value <= 59):
            raise serializers.ValidationError("Minuto deve estar entre 0 e 59")
        
        return value

    def validate_catra_timeout(self, value):
        # Aceita None ou string vazia como válidos (campo opcional)
        if value is None or value == '':
            return value
        
        # Converte para int se for string (vem do HTML form)
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                raise serializers.ValidationError("Timeout deve ser um número inteiro")
        
        # Valida o range numérico
        if not (1 <= value <= 60000):
            raise serializers.ValidationError(
                "Timeout deve estar entre 1 e 60000 milissegundos"
            )
        
        return value

    def to_internal_value(self, data):
        """
        CORREÇÃO: Trata campos booleanos ausentes no formulário HTML.
        Em updates parciais, campos checkbox desmarcados não são enviados pelo navegador.
        """
        # IMPORTANTE: QueryDict do Django é imutável, precisa fazer cópia
        if hasattr(data, "_mutable"):
            # É um QueryDict do formulário HTML - faz cópia mutável
            data = data.copy()
        elif not isinstance(data, dict):
            # Converte para dict normal se for outro tipo
            data = dict(data)

        boolean_fields = {
            "clear_expired_users": False,
            "url_reboot_enabled": True,
            "keep_user_image": True,
            "online": True,
            "local_identification": True,
            "web_server_enabled": True,
        }

        # Em updates parciais, define campos ausentes com seus valores default
        if self.partial:
            for field, default_value in boolean_fields.items():
                if field not in data:
                    data[field] = default_value

        return super().to_internal_value(data)
