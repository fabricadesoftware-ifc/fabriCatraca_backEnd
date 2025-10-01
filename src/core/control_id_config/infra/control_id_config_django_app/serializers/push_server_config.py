from rest_framework import serializers
from ..models import PushServerConfig


class PushServerConfigSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)

    class Meta:
        model = PushServerConfig
        fields = [
            "id",
            "device",
            "device_name",
            "push_request_timeout",
            "push_request_period",
            "push_remote_address",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_push_request_timeout(self, value):
        """Valida timeout em milissegundos"""
        if value < 0:
            raise serializers.ValidationError("Timeout não pode ser negativo")
        if value > 300000:  # 5 minutos
            raise serializers.ValidationError("Timeout não pode ser maior que 300000ms (5 minutos)")
        return value

    def validate_push_request_period(self, value):
        """Valida período em segundos"""
        if value < 0:
            raise serializers.ValidationError("Período não pode ser negativo")
        if value > 86400:  # 24 horas
            raise serializers.ValidationError("Período não pode ser maior que 86400s (24 horas)")
        return value

    def validate_push_remote_address(self, value):
        """Valida formato do endereço remoto (opcional: IP:porta)"""
        if value and value.strip():
            # Formato esperado: 192.168.120.94:80 ou hostname:porta
            if ':' not in value:
                raise serializers.ValidationError(
                    "Endereço remoto deve estar no formato 'IP:porta' ou 'hostname:porta'"
                )
            
            parts = value.split(':')
            if len(parts) != 2:
                raise serializers.ValidationError(
                    "Endereço remoto deve estar no formato 'IP:porta' ou 'hostname:porta'"
                )
            
            # Valida porta
            try:
                port = int(parts[1])
                if port < 1 or port > 65535:
                    raise serializers.ValidationError("Porta deve estar entre 1 e 65535")
            except ValueError:
                raise serializers.ValidationError("Porta deve ser um número válido")
        
        return value

    def to_representation(self, instance):
        """Customiza a representação de saída"""
        representation = super().to_representation(instance)
        
        # Converte timeout de ms para segundos para exibição
        representation['push_request_timeout_seconds'] = instance.push_request_timeout / 1000
        
        # Adiciona informação se push está configurado
        representation['is_configured'] = bool(instance.push_remote_address and instance.push_remote_address.strip())
        
        return representation
