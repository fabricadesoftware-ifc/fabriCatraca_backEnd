from rest_framework import serializers
from .models import MonitorConfig


class MonitorConfigSerializer(serializers.ModelSerializer):
    """
    Serializer para MonitorConfig - Sistema de Push de Logs em Tempo Real
    """
    device_name = serializers.CharField(source='device.name', read_only=True)
    is_configured = serializers.BooleanField(read_only=True)
    full_url = serializers.CharField(read_only=True)

    class Meta:
        model = MonitorConfig
        fields = [
            'id', 
            'device', 
            'device_name',
            'request_timeout', 
            'hostname', 
            'port', 
            'path',
            'is_configured',
            'full_url',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_request_timeout(self, value):
        """Valida o timeout (máximo 30 segundos)"""
        if value < 0:
            raise serializers.ValidationError("Timeout não pode ser negativo")
        if value > 30000:  # 30 segundos
            raise serializers.ValidationError("Timeout não pode exceder 30000ms (30 segundos)")
        return value
    
    def validate_port(self, value):
        """Valida a porta se fornecida"""
        if value and value.strip():
            try:
                port_int = int(value)
                if port_int < 1 or port_int > 65535:
                    raise serializers.ValidationError("Porta deve estar entre 1 e 65535")
            except ValueError:
                raise serializers.ValidationError("Porta deve ser um número válido")
        return value
    
    def validate(self, data):
        """
        Validação cruzada: se configurar hostname, deve configurar porta também
        """
        hostname = data.get('hostname', '')
        port = data.get('port', '')
        
        if hostname and hostname.strip() and not port:
            raise serializers.ValidationError({
                'port': 'Porta é obrigatória quando hostname é configurado'
            })
        
        return data
    
    def to_representation(self, instance):
        """Adiciona informações extras na resposta"""
        data = super().to_representation(instance)
        
        # Adiciona status de configuração
        if instance.is_configured:
            data['status'] = 'configured'
            data['notification_url'] = instance.full_url
        else:
            data['status'] = 'not_configured'
            data['notification_url'] = None
        
        return data
