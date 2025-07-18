from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

from src.core.__seedwork__.infra import ControlIDSyncMixin

class TimeZoneSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("time_zones", [{
            "id": instance.id,
            "name": instance.name
        }])
        return response

    def update_in_catraca(self, instance):
        response = self.update_objects(
            "time_zones",
            {
                "id": instance.id,
                "name": instance.name
            },
            {"time_zones": {"id": instance.id}}
        )
        return response

    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "time_zones",
            {"time_zones": {"id": instance.id}}
        )
        return response

    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import TimeZone
            
            catraca_objects = self.load_objects(
                "time_zones",
                fields=["id", "name"]
            )

            with transaction.atomic():
                TimeZone.objects.all().delete()
                for data in catraca_objects:
                    TimeZone.objects.create(
                        id=data["id"],
                        name=data["name"]
                    )

            return Response({
                "success": True,
                "message": f"Sincronizadas {len(catraca_objects)} zonas de tempo"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)