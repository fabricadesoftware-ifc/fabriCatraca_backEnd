from rest_framework import serializers

from .models import MonitorAlert, MonitorConfig


class MonitorConfigSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)
    is_configured = serializers.BooleanField(read_only=True)
    full_url = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = MonitorConfig
        fields = [
            "id",
            "device",
            "device_name",
            "request_timeout",
            "hostname",
            "port",
            "path",
            "heartbeat_timeout_seconds",
            "last_seen_at",
            "last_payload_at",
            "last_signal_source",
            "offline_since",
            "offline_detection_paused_until",
            "is_offline",
            "is_configured",
            "full_url",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "last_seen_at",
            "last_payload_at",
            "last_signal_source",
            "offline_since",
            "offline_detection_paused_until",
            "is_offline",
            "created_at",
            "updated_at",
        ]

    def validate_request_timeout(self, value):
        if value < 0:
            raise serializers.ValidationError("Timeout nao pode ser negativo")
        if value > 30000:
            raise serializers.ValidationError("Timeout nao pode exceder 30000ms (30 segundos)")
        return value

    def validate_heartbeat_timeout_seconds(self, value):
        if value < 30:
            raise serializers.ValidationError("Heartbeat timeout deve ser no minimo 30 segundos")
        if value > 86400:
            raise serializers.ValidationError("Heartbeat timeout nao pode exceder 86400 segundos")
        return value

    def validate_port(self, value):
        if value and value.strip():
            try:
                port_int = int(value)
                if port_int < 1 or port_int > 65535:
                    raise serializers.ValidationError("Porta deve estar entre 1 e 65535")
            except ValueError as exc:
                raise serializers.ValidationError("Porta deve ser um numero valido") from exc
        return value

    def validate(self, data):
        hostname = data.get("hostname", "")
        port = data.get("port", "")
        if hostname and hostname.strip() and not port:
            raise serializers.ValidationError({"port": "Porta e obrigatoria quando hostname e configurado"})
        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["notification_url"] = instance.full_url if instance.is_configured else None
        return data


class MonitorAlertSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)
    user_name = serializers.CharField(source="user.name", read_only=True)
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = MonitorAlert
        fields = [
            "id",
            "type",
            "severity",
            "title",
            "message",
            "device",
            "device_name",
            "user",
            "user_name",
            "dedupe_key",
            "metadata",
            "started_at",
            "resolved_at",
            "is_active",
            "created_at",
            "updated_at",
            "is_read",
        ]
        read_only_fields = fields

    def get_is_read(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return True
        return obj.reads.filter(user=user).exists()
