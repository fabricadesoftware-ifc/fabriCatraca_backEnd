from rest_framework import serializers
from ..models.portal import Portal

class PortalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portal
        fields = ['id', 'name'] 
        read_only_fields = ['id']