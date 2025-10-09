from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import Portal, Area


class AreaBasicSerializer(serializers.ModelSerializer):
    """Serializer para exibir informações básicas de áreas"""
    class Meta:
        model = Area
        fields = ['id', 'name']


class PortalSerializer(serializers.ModelSerializer):
    # ✅ Saída: mostra os dados completos das áreas
    area_from_detail = AreaBasicSerializer(source='area_from', read_only=True)
    area_to_detail = AreaBasicSerializer(source='area_to', read_only=True)
    
    # ✅ Entrada: permite enviar apenas os IDs das áreas
    area_from = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(),
        required=True
    )
    area_to = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(),
        required=True
    )
    
    class Meta:
        model = Portal
        fields = ['id', 'name', 'area_from', 'area_to', 'area_from_detail', 'area_to_detail'] 
        read_only_fields = ['id', 'area_from_detail', 'area_to_detail']
    
    def to_representation(self, instance):
        """Customiza a saída para mostrar os detalhes das áreas"""
        representation = super().to_representation(instance)
        # Na saída, mover os detalhes para os campos principais
        representation['area_from'] = representation.pop('area_from_detail')
        representation['area_to'] = representation.pop('area_to_detail')
        return representation