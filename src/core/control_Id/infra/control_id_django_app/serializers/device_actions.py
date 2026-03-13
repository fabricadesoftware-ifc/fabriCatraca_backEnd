from rest_framework import serializers


class DeviceActionBaseSerializer(serializers.Serializer):
    device_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )


class MessageToScreenSerializer(DeviceActionBaseSerializer):
    message = serializers.CharField(allow_blank=True)
    timeout = serializers.IntegerField(min_value=0)


class BuzzerBuzzSerializer(DeviceActionBaseSerializer):
    frequency = serializers.IntegerField(min_value=1)
    duty_cycle = serializers.IntegerField(min_value=1, max_value=100)
    timeout = serializers.IntegerField(min_value=1, max_value=3000)


class RemoteActionItemSerializer(serializers.Serializer):
    action = serializers.CharField()
    parameters = serializers.CharField(allow_blank=True)


class RemoteUserAuthorizationSerializer(DeviceActionBaseSerializer):
    event = serializers.IntegerField()
    user_id = serializers.IntegerField(min_value=0, required=False, default=0)
    user_name = serializers.CharField(
        allow_blank=True,
        required=False,
        default="",
    )
    user_image = serializers.BooleanField(required=False, default=False)
    portal_id = serializers.IntegerField(min_value=1)
    actions = RemoteActionItemSerializer(many=True, allow_empty=False)
