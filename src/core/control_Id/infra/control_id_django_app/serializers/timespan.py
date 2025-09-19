from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import TimeSpan
from src.core.control_Id.infra.control_id_django_app.serializers import TimeZoneSerializer

class TimeSpanSerializerList(serializers.ModelSerializer):
    time_zone = TimeZoneSerializer()

    class Meta:
        model = TimeSpan
        fields = ['id', 'time_zone', 'start', 'end', 'sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'hol1', 'hol2', 'hol3'] 
        read_only_fields = ['id']
        depth = 1
        
class TimeSpanSerializerCreateUpdate(serializers.ModelSerializer):
    class Meta:
        model = TimeSpan
        fields = ['id', 'time_zone', 'start', 'end', 'sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'hol1', 'hol2', 'hol3'] 
        read_only_fields = ['id']