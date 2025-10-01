from rest_framework import serializers
from ..models import HardwareConfig


class HardwareConfigSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)
    
    # CORREÇÃO: Campos booleanos explícitos para corrigir comportamento do HTML form do DRF
    # Quando checkbox está desmarcado, HTML form não envia nada
    # required=False permite campo ausente, default=False interpreta ausência como False
    beep_enabled = serializers.BooleanField(required=False, default=False)
    ssh_enabled = serializers.BooleanField(required=False, default=False)
    relayN_enabled = serializers.BooleanField(required=False, default=False)
    relayN_auto_close = serializers.BooleanField(required=False, default=True)
    door_sensorN_enabled = serializers.BooleanField(required=False, default=False)
    doorN_interlock = serializers.BooleanField(required=False, default=False)
    bell_enabled = serializers.BooleanField(required=False, default=False)
    exception_mode = serializers.BooleanField(required=False, default=False)
    doorN_exception_mode = serializers.BooleanField(required=False, default=False)
    
    class Meta:
        model = HardwareConfig
        fields = [
            'id', 'device', 'device_name',
            'beep_enabled', 'ssh_enabled', 'relayN_enabled', 'relayN_timeout',
            'relayN_auto_close', 'door_sensorN_enabled', 'door_sensorN_idle',
            'doorN_interlock', 'bell_enabled', 'bell_relay',
            'exception_mode', 'doorN_exception_mode'
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'device': {'required': False},  # Não obrigatório em updates
            'relayN_timeout': {'required': False},
            'door_sensorN_idle': {'required': False},
            'bell_relay': {'required': False}
        }
        
    def validate_relayN_timeout(self, value):
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
        if not (1 <= value <= 60):
            raise serializers.ValidationError("Timeout do relé deve estar entre 1 e 60 segundos")
        
        return value
        
    def validate_door_sensorN_idle(self, value):
        # Aceita None ou string vazia como válidos (campo opcional)
        if value is None or value == '':
            return value
        
        # Converte para int se for string (vem do HTML form)
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                raise serializers.ValidationError("Tempo deve ser um número inteiro")
        
        # Valida o range numérico
        if not (1 <= value <= 300):
            raise serializers.ValidationError("Tempo de inatividade do sensor deve estar entre 1 e 300 segundos")
        
        return value
    
    def to_internal_value(self, data):
        """
        CORREÇÃO: Trata campos booleanos ausentes no formulário HTML.
        Em updates parciais, campos checkbox desmarcados não são enviados pelo navegador.
        """
        # IMPORTANTE: QueryDict do Django é imutável, precisa fazer cópia
        if hasattr(data, '_mutable'):
            # É um QueryDict do formulário HTML - faz cópia mutável
            data = data.copy()
        elif not isinstance(data, dict):
            # Converte para dict normal se for outro tipo
            data = dict(data)
        
        boolean_fields = {
            'beep_enabled': False,
            'ssh_enabled': False,
            'relayN_enabled': False,
            'relayN_auto_close': True,  # Único que tem default True
            'door_sensorN_enabled': False,
            'doorN_interlock': False,
            'bell_enabled': False,
            'exception_mode': False,
            'doorN_exception_mode': False
        }
        
        # Em updates parciais, define campos ausentes com seus valores default
        if self.partial:
            for field, default_value in boolean_fields.items():
                if field not in data:
                    data[field] = default_value
        
        return super().to_internal_value(data)