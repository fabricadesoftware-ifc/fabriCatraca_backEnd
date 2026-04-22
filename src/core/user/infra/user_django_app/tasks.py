from celery import shared_task

from .models import Visitas
from .visit_service import VisitService


@shared_task(bind=True)
def expire_visit(self, visit_id: int):
    try:
        visit = Visitas.objects.select_related("user", "card").get(pk=visit_id)
    except Visitas.DoesNotExist:
        return {"status": "missing", "visit_id": visit_id}

    service = VisitService()
    service.close_visit(visit)
    return {"status": "closed", "visit_id": visit_id}
