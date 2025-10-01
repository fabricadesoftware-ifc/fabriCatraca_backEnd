from rest_framework import serializers
from ..models import SecurityConfig


class SecurityConfigSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)
    
    # CORREÇÃO: Campos booleanos explícitos para corrigir comportamento do HTML form do DRF
    # required=False permite campo ausente, default define valor quando ausente
    password_only = serializers.BooleanField(required=False, default=False)
    hide_password_only = serializers.BooleanField(required=False, default=False)
    hide_name_on_identification = serializers.BooleanField(required=False, default=False)
    send_code_when_not_identified = serializers.BooleanField(required=False, default=False)
    send_code_when_not_authorized = serializers.BooleanField(required=False, default=False)
    
    class Meta:
        model = SecurityConfig
        fields = [
            'id', 'device', 'device_name',
            'password_only', 'hide_password_only', 'password_only_tip',
            'hide_name_on_identification', 'denied_transaction_code',
            'send_code_when_not_identified', 'send_code_when_not_authorized'
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'device': {'required': False},  # Não obrigatório em updates
            'password_only_tip': {'required': False},  # Campo de texto opcional
            'denied_transaction_code': {'required': False}  # Campo numérico opcional
        }
        
    def validate_denied_transaction_code(self, value):
        # Aceita None, string vazia ou '0' como válidos (campo opcional/não configurado)
        if value is None or value == '' or value == '0' or value == 0:
            return ''  # Retorna string vazia para indicar "não configurado"
        
        # Converte para int se for string (vem do HTML form)
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                raise serializers.ValidationError("Código deve ser um número inteiro")
        
        # Valida o range numérico (1-999, zero não é válido como código)
        if not (1 <= value <= 999):
            raise serializers.ValidationError("Código deve estar entre 1 e 999")
        
        return value
    
    def to_internal_value(self, data):
        """
        CORREÇÃO: Trata campos booleanos ausentes no formulário HTML.
        Em updates parciais, campos checkbox desmarcados não são enviados pelo navegador.
        """
        # IMPORTANTE: QueryDict do Django é imutável, precisa fazer cópia
        if hasattr(data, '_mutable'):
            data = data.copy()
        elif not isinstance(data, dict):
            data = dict(data)
        
        boolean_fields = {
            'password_only': False,
            'hide_password_only': False,
            'hide_name_on_identification': False,
            'send_code_when_not_identified': False,
            'send_code_when_not_authorized': False
        }
        
        # Em updates parciais, define campos ausentes com seus valores default
        if self.partial:
            for field, default_value in boolean_fields.items():
                if field not in data:
                    data[field] = default_value
        
        return super().to_internal_value(data)