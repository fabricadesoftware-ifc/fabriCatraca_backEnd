from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

class TimeSpanSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("time_spans", [{
            "id": instance.id,
            "time_zone_id": instance.time_zone.id,
            "start": instance.start,
            "end": instance.end,
            "sun": instance.sun,
            "mon": instance.mon,
            "tue": instance.tue,
            "wed": instance.wed,
            "thu": instance.thu,
            "fri": instance.fri,
            "sat": instance.sat,
            "hol1": instance.hol1,
            "hol2": instance.hol2,
            "hol3": instance.hol3
        }])
        return response

    def update_in_catraca(self, instance):
        response = self.update_objects(
            "time_spans",
            {
                "id": instance.id,
                "time_zone_id": instance.time_zone.id,
                "start": instance.start,
                "end": instance.end,
                "sun": instance.sun,
                "mon": instance.mon,
                "tue": instance.tue,
                "wed": instance.wed,
                "thu": instance.thu,
                "fri": instance.fri,
                "sat": instance.sat,
                "hol1": instance.hol1,
                "hol2": instance.hol2,
                "hol3": instance.hol3
            },
            {"time_spans": {"id": instance.id}}
        )
        return response

    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "time_spans",
            {"time_spans": {"id": instance.id}}
        )
        return response

    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import TimeSpan, TimeZone
            
            catraca_objects = self.load_objects("time_spans")

            with transaction.atomic():
                TimeSpan.objects.all().delete()
                for data in catraca_objects:
                    time_zone = TimeZone.objects.get(id=data["time_zone_id"])
                    TimeSpan.objects.create(
                        id=data["id"],
                        time_zone=time_zone,
                        start=data["start"],
                        end=data["end"],
                        sun=data.get("sun", False),
                        mon=data.get("mon", False),
                        tue=data.get("tue", False),
                        wed=data.get("wed", False),
                        thu=data.get("thu", False),
                        fri=data.get("fri", False),
                        sat=data.get("sat", False),
                        hol1=data.get("hol1", False),
                        hol2=data.get("hol2", False),
                        hol3=data.get("hol3", False)
                    )

            return Response({
                "success": True,
                "message": f"Sincronizados {len(catraca_objects)} intervalos de tempo"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
