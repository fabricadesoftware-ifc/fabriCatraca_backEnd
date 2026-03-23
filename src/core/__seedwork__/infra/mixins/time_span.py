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
            "sun": int(instance.sun),  # Converte boolean para int (0/1)
            "mon": int(instance.mon),
            "tue": int(instance.tue),
            "wed": int(instance.wed),
            "thu": int(instance.thu),
            "fri": int(instance.fri),
            "sat": int(instance.sat),
            "hol1": int(instance.hol1),
            "hol2": int(instance.hol2),
            "hol3": int(instance.hol3)
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
                "sun": int(instance.sun),  # Converte boolean para int (0/1)
                "mon": int(instance.mon),
                "tue": int(instance.tue),
                "wed": int(instance.wed),
                "thu": int(instance.thu),
                "fri": int(instance.fri),
                "sat": int(instance.sat),
                "hol1": int(instance.hol1),
                "hol2": int(instance.hol2),
                "hol3": int(instance.hol3)
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
