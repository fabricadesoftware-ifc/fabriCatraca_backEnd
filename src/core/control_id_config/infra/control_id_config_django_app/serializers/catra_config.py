from rest_framework import serializers
from ..models import CatraConfig


class CatraConfigSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)

    # Campos booleanos explícitos para corrigir comportamento do HTML form do DRF
    anti_passback = serializers.BooleanField(required=False, default=False)
    daily_reset = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = CatraConfig
        fields = [
            "id",
            "device",
            "device_name",
            "anti_passback",
            "daily_reset",
            "gateway",
            "operation_mode",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_gateway(self, value):
        """Valida o sentido do gateway"""
        valid_gateways = ['clockwise', 'anticlockwise']
        if value not in valid_gateways:
            raise serializers.ValidationError(
                f"Gateway deve ser 'clockwise' ou 'anticlockwise'. Recebido: {value}"
            )
        return value

    def validate_operation_mode(self, value):
        """Valida o modo de operação"""
        valid_modes = ['blocked', 'entrance_open', 'exit_open', 'both_open']
        if value not in valid_modes:
            raise serializers.ValidationError(
                f"Operation mode deve ser um de: {', '.join(valid_modes)}. Recebido: {value}"
            )
        return value

    def to_representation(self, instance):
        """Customiza a representação de saída"""
        representation = super().to_representation(instance)
        
        # Traduz gateway para português
        gateway_translations = {
            'clockwise': 'Horário',
            'anticlockwise': 'Anti-horário'
        }
        representation['gateway_display'] = gateway_translations.get(
            instance.gateway, 
            instance.gateway
        )
        
        # Traduz operation_mode para português
        mode_translations = {
            'blocked': 'Ambas controladas',
            'entrance_open': 'Entrada liberada',
            'exit_open': 'Saída liberada',
            'both_open': 'Ambas liberadas'
        }
        representation['operation_mode_display'] = mode_translations.get(
            instance.operation_mode,
            instance.operation_mode
        )
        
        return representation
