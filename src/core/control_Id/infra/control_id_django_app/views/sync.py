from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction
from django.db.utils import OperationalError
from time import sleep
from datetime import datetime

from src.core.user.infra.user_django_app.models import User

from src.core.__seedwork__.infra import ControlIDSyncMixin
from drf_spectacular.utils import extend_schema
from celery.result import AsyncResult

class GlobalSyncMixin(ControlIDSyncMixin):
    """Mixin para sincronização global com as catracas"""
    
    def sync_users(self, device):
        """Sincroniza usuários"""
        users = self.load_objects(
            "users",
            fields=["id", "name", "registration", "user_type_id"],
            order_by=["id"]
        )
        return users

    def sync_time_zones(self, device):
        """Sincroniza zonas de tempo"""
        time_zones = self.load_objects(
            "time_zones",
            fields=["id", "name"],
            order_by=["id"]
        )
        return time_zones

    def sync_time_spans(self, device):
        """Sincroniza intervalos de tempo"""
        time_spans = self.load_objects(
            "time_spans",
            fields=["id", "time_zone_id", "start", "end", "sun", "mon", "tue", "wed", "thu", "fri", "sat", "hol1", "hol2", "hol3"],
            order_by=["id"]
        )
        return time_spans

    def sync_access_rules(self, device):
        """Sincroniza regras de acesso"""
        access_rules = self.load_objects(
            "access_rules",
            fields=["id", "name", "type", "priority"],
            order_by=["id"]
        )
        return access_rules

    def sync_portals(self, device):
        """Sincroniza portais"""
        portals = self.load_objects(
            "portals",
            fields=["id", "name", "area_from_id", "area_to_id"],
            order_by=["id"]
        )
        return portals

    def sync_areas(self, device):
        """Sincroniza áreas"""
        areas = self.load_objects(
            "areas",
            fields=["id", "name"],
            order_by=["id"]
        )
        return areas

    def sync_templates(self, device):
        """Sincroniza templates"""
        templates = self.load_objects(
            "templates",
            fields=["user_id", "template", "finger_type", "finger_position"],
            order_by=["user_id"]
        )
        return templates

    def sync_cards(self, device):
        """Sincroniza cartões"""
        cards = self.load_objects(
            "cards",
            fields=["user_id", "value"],
            order_by=["user_id"]
        )
        return cards

    def sync_user_access_rules(self, device):
        """Sincroniza regras de acesso de usuários"""
        rules = self.load_objects(
            "user_access_rules",
            fields=["user_id", "access_rule_id"],
            order_by=["user_id", "access_rule_id"]
        )
        return rules

    def sync_portal_access_rules(self, device):
        """Sincroniza regras de acesso de portais"""
        rules = self.load_objects(
            "portal_access_rules",
            fields=["portal_id", "access_rule_id"],
            order_by=["portal_id", "access_rule_id"]
        )
        return rules

    def sync_access_rule_time_zones(self, device):
        """Sincroniza zonas de tempo das regras de acesso"""
        rules = self.load_objects(
            "access_rule_time_zones",
            fields=["access_rule_id", "time_zone_id"],
            order_by=["access_rule_id", "time_zone_id"]
        )
        return rules

    def sync_user_groups(self, device):
        """Sincroniza usuários em grupos"""
        user_groups = self.load_objects(
            "user_groups",
            fields=["user_id", "group_id"],
            order_by=["user_id", "group_id"]
        )
        return user_groups
    def sync_groups(self, device):
        """Sincroniza grupos"""
        groups = self.load_objects(
            "groups",
            fields=["id", "name"],
            order_by=["id"]
        )
        return groups
    
    def sync_group_access_rules(self, device):
        """Sincroniza grupos de acesso"""
        group_access_rules = self.load_objects(
            "group_access_rules",
            fields=["group_id", "access_rule_id"],
            order_by=["group_id", "access_rule_id"]
        )
        return group_access_rules

    def sync_access_logs(self, device):
        """Sincroniza logs de acesso"""
        access_logs = self.load_objects(
            "access_logs",
            fields=["id", "time", "event", "device_id", "identifier_id", "user_id", "portal_id", "identification_rule_id", "qrcode_value", "uhf_tag", "pin_value", "card_value"],
            order_by=["id"]
        )
        return access_logs

@extend_schema(tags=["Config"])
@api_view(['GET'])
def sync_all(request):
    """Dispara sincronização global de forma assíncrona via Celery"""
    # Import local para evitar import circular com tasks
    from ..tasks import run_global_sync
    task = run_global_sync.delay()
    return Response({
        "task_id": task.id,
        "status": "queued"
    }, status=status.HTTP_202_ACCEPTED)


@extend_schema(tags=["Config"]) 
@api_view(['GET'])
def sync_status(request):
    task_id = request.query_params.get('task_id')
    if not task_id:
        return Response({"error": "task_id é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)
    result = AsyncResult(task_id)
    payload = {
        "task_id": task_id,
        "state": result.state,
    }
    if result.successful():
        payload["result"] = result.result
    elif result.failed():
        payload["error"] = str(result.result)
    return Response(payload)