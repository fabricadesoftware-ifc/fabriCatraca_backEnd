from rest_framework import serializers
from ..models import CatraConfig


class CatraConfigSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)

    # Campos booleanos explícitos para corrigir comportamento do HTML form do DRF
    anti_passback = serializers.BooleanField(required=False, default=False)
    daily_reset = serializers.BooleanField(required=False, default=False)
    
    # Campos de escolha explícitos para garantir limpeza de dados
    gateway = serializers.ChoiceField(
        choices=['clockwise', 'anticlockwise'],
        required=False,
        default='clockwise'
    )
    operation_mode = serializers.ChoiceField(
        choices=['blocked', 'entrance_open', 'exit_open', 'both_open'],
        required=False,
        default='blocked'
    )

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
        """Limpa e valida o sentido do gateway"""
        if value:
            # Remove aspas extras e espaços
            value = value.strip().strip('"').strip("'")
        return value

    def validate_operation_mode(self, value):
        """Limpa e valida o modo de operação"""
        if value:
            # Remove aspas extras e espaços
            value = value.strip().strip('"').strip("'")
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
