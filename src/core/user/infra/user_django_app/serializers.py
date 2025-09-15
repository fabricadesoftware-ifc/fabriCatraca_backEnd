from rest_framework import serializers
from .models import User
from src.core.control_Id.infra.control_id_django_app.serializers.device import DeviceSerializer
from src.core.control_Id.infra.control_id_django_app.models.device import Device
from django.contrib.auth.models import Group

class UserSerializer(serializers.ModelSerializer):
    devices = DeviceSerializer(many=True, read_only=True)
    user_groups = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'registration', 'user_type_id', 'devices', 'user_groups']

    def get_user_groups(self, obj):
        return [{"id": group.id, "name": group.name} for group in Group.objects.filter(usergroup__user=obj)]