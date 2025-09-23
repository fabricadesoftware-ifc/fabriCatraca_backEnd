from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import AccessLogs, Device, Portal, AccessRule
from src.core.user.infra.user_django_app.models import User

class DeviceMinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id', 'name']

class UserMinSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'registration']

class PortalMinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portal
        fields = ['id', 'name']

class AccessRuleMinSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRule
        fields = ['id', 'name']

class AccessLogsSerializer(serializers.ModelSerializer):
    device = DeviceMinSerializer(read_only=True)
    user = UserMinSerializer(read_only=True)
    portal = PortalMinSerializer(read_only=True)
    access_rule = AccessRuleMinSerializer(read_only=True)

    class Meta:
        model = AccessLogs
        fields = ['id', 'time', 'event_type', 'device', 'identifier_id', 'user', 'portal', 'access_rule', 'qr_code', 'uhf_value', 'pin_value', 'card_value', 'confidence', 'mask']
        read_only_fields = ['id']

    def to_representation(self, instance):
        # Se estiver listando múltiplos registros, use uma versão simplificada
        if isinstance(self.instance, (list, AccessLogs.objects.none().__class__)) or self.many:
            return {
                'id': instance.id,
                'time': instance.time,
                'event_type': instance.event_type,
                'device_id': instance.device_id,
                'device_name': instance.device.name if instance.device else None,
                'user_id': instance.user_id,
                'user_name': instance.user.name if instance.user else None,
                'portal_id': instance.portal_id,
                'portal_name': instance.portal.name if instance.portal else None,
            }
        # Se for um registro único, retorna todos os campos
        return super().to_representation(instance)

