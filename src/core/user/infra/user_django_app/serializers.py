from rest_framework import serializers
from .models import User
from src.core.control_Id.infra.control_id_django_app.serializers.device import DeviceSerializer
from src.core.control_Id.infra.control_id_django_app.models.device import Device

class UserSerializer(serializers.ModelSerializer):
    devices = DeviceSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'registration', 'user_type_id', 'devices']