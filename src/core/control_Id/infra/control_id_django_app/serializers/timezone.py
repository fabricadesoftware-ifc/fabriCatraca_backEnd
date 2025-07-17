from rest_framework import serializers
from ..models.timezone import TimeZone

class TimeZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeZone
        fields = ['id', 'name'] 