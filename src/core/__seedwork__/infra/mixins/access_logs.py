from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

class AccessLogsSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("access_logs", [{
            "id": instance.id,
            "time": instance.time,
            "event": instance.event_type,
            "device": instance.device,
            "identifier_id": instance.identifier_id,
            "user": instance.user,
            "portal": instance.portal,
            "access_rule": instance.access_rule,
            "qr_code": instance.qr_code,
            "uhf_value": instance.uhf_value,
            "pin_value": instance.pin_value,
            "card_value": instance.card_value,
            "confidence": instance.confidence,
            "mask": instance.mask
        }])
        return response
    
    def update_in_catraca(self, instance):
        response = self.update_objects(
            "access_logs",
            {
                "id": instance.id,
                "time": instance.time,
                "event": instance.event_type,
                "device": instance.device,
                "identifier_id": instance.identifier_id,
                "user": instance.user,
                "portal": instance.portal,
                "access_rule": instance.access_rule,
                "qr_code": instance.qr_code,
                "uhf_value": instance.uhf_value,
                "pin_value": instance.pin_value,
                "card_value": instance.card_value,
                "confidence": instance.confidence,
                "mask": instance.mask
            },
            {"access_logs": {"id": instance.id}}
        )
        return response
    
    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "access_logs",
            {"access_logs": {"id": instance.id}}
        )
        return response
    
    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import AccessLogs
            
            catraca_objects = self.load_objects("access_logs")

            with transaction.atomic():
                AccessLogs.objects.all().delete()
                for data in catraca_objects:
                    AccessLogs.objects.create(
                        id=data["id"],
                        time=data["time"],
                        event_type=data["event"],
                        device=data["device_id"],
                        identifier_id=data["identifier_id"],
                        user=data["user_id"],
                        portal=data["portal_id"],
                        access_rule=data["identification_rule_id"],
                        qr_code=data["qr_code"],
                        uhf_value=data["uhf_value"] if data["uhf_value"] else "",
                        pin_value=data["pin_value"] if data["pin_value"] else None,
                        card_value=data["card_value"] if data["card_value"] else "",
                        confidence=data["confidence"] if data["confidence"] else 0,
                        mask=data["mask"] if data["mask"] else ""
                    )

            return Response({
                "success": True,
                "message": f"Sincronizados {len(catraca_objects)} logs de acesso"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
        
