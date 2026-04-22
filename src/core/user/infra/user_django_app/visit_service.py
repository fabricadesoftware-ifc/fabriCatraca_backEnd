from django.db import transaction
from django.utils import timezone
from rest_framework import status

from src.core.__seedwork__.infra.mixins import CardSyncMixin

from .models import Visitas


class VisitService(CardSyncMixin):
    def close_visit(self, visit: Visitas):
        if visit.finished_at:
            return visit

        with transaction.atomic():
            if visit.card and not visit.card_removed_at:
                devices = visit.user.get_target_devices(include_inactive=False)
                for device in devices:
                    self.set_device(device)
                    response = self.delete_in_catraca(visit.card)
                    if response.status_code != status.HTTP_204_NO_CONTENT:
                        raise RuntimeError(
                            f"Falha ao remover cartao da visita na catraca {device.name}: {response.data}"
                        )

                visit.card_removed_at = timezone.now()

            visit.finished_at = timezone.now()
            visit.save(update_fields=["finished_at", "card_removed_at", "updated_at"])

        return visit
