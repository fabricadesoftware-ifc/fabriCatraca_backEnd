from rest_framework import serializers
from ..models.timespan import TimeSpan

class TimeSpanSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeSpan
        fields = ['id', 'time_zone', 'start', 'end', 'sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'hol1', 'hol2', 'hol3'] 