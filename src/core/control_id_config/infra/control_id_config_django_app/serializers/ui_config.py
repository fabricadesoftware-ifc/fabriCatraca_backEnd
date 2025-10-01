from rest_framework import serializers
from ..models import UIConfig


class UIConfigSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)
    
    # CORREÇÃO: Campos booleanos explícitos para corrigir comportamento do HTML form do DRF
    # required=False permite campo ausente, default define valor quando ausente
    screen_always_on = serializers.BooleanField(required=False, default=False)
    
    class Meta:
        model = UIConfig
        fields = [
            'id', 'device', 'device_name',
            'screen_always_on'
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'device': {'required': False}  # Não obrigatório em updates
        }
    
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
            'screen_always_on': False
        }
        
        # Em updates parciais, define campos ausentes com seus valores default
        if self.partial:
            for field, default_value in boolean_fields.items():
                if field not in data:
                    data[field] = default_value
        
        return super().to_internal_value(data)