from rest_framework import serializers
from ..models.template import Template

class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ['id', 'user', 'template', 'finger_type', 'finger_position']
        read_only_fields = ['id', 'template', 'finger_type', 'finger_position']