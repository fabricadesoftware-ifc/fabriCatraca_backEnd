from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import UserGroup


class UserGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserGroup
        fields = ['id', 'user', 'group']
        read_only_fields = ['id']
        