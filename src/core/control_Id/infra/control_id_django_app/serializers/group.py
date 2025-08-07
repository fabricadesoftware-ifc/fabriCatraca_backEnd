from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import CustomGroup

class CustomGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomGroup
        fields = ['id', 'name']
        read_only_fields = ['id']