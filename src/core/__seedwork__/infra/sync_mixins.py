from rest_framework import status
from rest_framework.response import Response
from django.db import transaction
from .catraca_sync import CatracaSyncMixin

class BaseSyncMixin(CatracaSyncMixin):
    """
    Mixin base que implementa os métodos comuns de sincronização
    """
    def perform_create(self, serializer):
        """
        Sobrescreve o método perform_create para sincronizar com a catraca
        """
        instance = serializer.save()
        response = self.create_in_catraca(instance)
        if response.status_code != status.HTTP_201_CREATED:
            instance.delete()
            raise Exception(response.data.get('error', 'Erro ao criar na catraca'))
        return instance

    def perform_update(self, serializer):
        """
        Sobrescreve o método perform_update para sincronizar com a catraca
        """
        instance = serializer.save()
        response = self.update_in_catraca(instance)
        if response.status_code != status.HTTP_200_OK:
            raise Exception(response.data.get('error', 'Erro ao atualizar na catraca'))
        return instance

    def perform_destroy(self, instance):
        """
        Sobrescreve o método perform_destroy para sincronizar com a catraca
        """
        response = self.delete_in_catraca(instance)
        if response.status_code != status.HTTP_204_NO_CONTENT:
            raise Exception(response.data.get('error', 'Erro ao deletar na catraca'))
        instance.delete()

class TimeZoneSyncMixin(BaseSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("time_zones", [{
            "id": instance.id,
            "name": instance.name
        }])
        return response

    def update_in_catraca(self, instance):
        response = self.update_objects(
            "time_zones",
            [{
                "id": instance.id,
                "name": instance.name
            }],
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

class TimeSpanSyncMixin(CatracaSyncMixin):
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
            [{
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
            }],
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

class AccessRuleSyncMixin(CatracaSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("access_rules", [{
            "id": instance.id,
            "name": instance.name,
            "type": instance.type,
            "priority": instance.priority
        }])
        return response

    def update_in_catraca(self, instance):
        response = self.update_objects(
            "access_rules",
            [{
                "id": instance.id,
                "name": instance.name,
                "type": instance.type,
                "priority": instance.priority
            }],
            {"access_rules": {"id": instance.id}}
        )
        return response

    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "access_rules",
            {"access_rules": {"id": instance.id}}
        )
        return response

    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import AccessRule
            
            catraca_objects = self.load_objects("access_rules")

            with transaction.atomic():
                AccessRule.objects.all().delete()
                for data in catraca_objects:
                    AccessRule.objects.create(
                        id=data["id"],
                        name=data["name"],
                        type=data["type"],
                        priority=data["priority"]
                    )

            return Response({
                "success": True,
                "message": f"Sincronizadas {len(catraca_objects)} regras de acesso"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserAccessRuleSyncMixin(CatracaSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("user_access_rules", [{
            "user_id": instance.user.id,
            "access_rule_id": instance.access_rule.id
        }])
        return response

    def update_in_catraca(self, instance):
        response = self.update_objects(
            "user_access_rules",
            [{
                "user_id": instance.user.id,
                "access_rule_id": instance.access_rule.id
            }],
            {"user_access_rules": {
                "user_id": instance.user.id,
                "access_rule_id": instance.access_rule.id
            }}
        )
        return response

    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "user_access_rules",
            {"user_access_rules": {
                "user_id": instance.user.id,
                "access_rule_id": instance.access_rule.id
            }}
        )
        return response

    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import UserAccessRule, AccessRule
            from src.core.user.infra.user_django_app.models import User
            
            catraca_objects = self.load_objects("user_access_rules")

            with transaction.atomic():
                UserAccessRule.objects.all().delete()
                for data in catraca_objects:
                    user = User.objects.get(id=data["user_id"])
                    access_rule = AccessRule.objects.get(id=data["access_rule_id"])
                    UserAccessRule.objects.create(
                        user=user,
                        access_rule=access_rule
                    )

            return Response({
                "success": True,
                "message": f"Sincronizadas {len(catraca_objects)} associações usuário-regra"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AccessRuleTimeZoneSyncMixin(BaseSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("access_rule_time_zones", [{
            "access_rule_id": instance.access_rule.id,
            "time_zone_id": instance.time_zone.id
        }])
        return response

    def update_in_catraca(self, instance):
        response = self.update_objects(
            "access_rule_time_zones",
            [{
                "access_rule_id": instance.access_rule.id,
                "time_zone_id": instance.time_zone.id
            }],
            {"access_rule_time_zones": {
                "access_rule_id": instance.access_rule.id,
                "time_zone_id": instance.time_zone.id
            }}
        )
        return response

    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "access_rule_time_zones",
            {"access_rule_time_zones": {
                "access_rule_id": instance.access_rule.id,
                "time_zone_id": instance.time_zone.id
            }}
        )
        return response

    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import AccessRuleTimeZone, AccessRule, TimeZone
            
            catraca_objects = self.load_objects(
                "access_rule_time_zones",
                fields=["access_rule_id", "time_zone_id"],
                order_by=["access_rule_id", "time_zone_id"]
            )

            with transaction.atomic():
                AccessRuleTimeZone.objects.all().delete()
                for data in catraca_objects:
                    AccessRuleTimeZone.objects.create(
                        access_rule=AccessRule.objects.get(id=data["access_rule_id"]),
                        time_zone=TimeZone.objects.get(id=data["time_zone_id"])
                    )

            return Response({
                "success": True,
                "message": f"Sincronizadas {len(catraca_objects)} associações regra-zona"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PortalAccessRuleSyncMixin(CatracaSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("portal_access_rules", [{
            "portal_id": instance.portal_id,
            "access_rule_id": instance.access_rule.id
        }])
        return response

    def update_in_catraca(self, instance):
        response = self.update_objects(
            "portal_access_rules",
            [{
                "portal_id": instance.portal_id,
                "access_rule_id": instance.access_rule.id
            }],
            {"portal_access_rules": {
                "portal_id": instance.portal_id,
                "access_rule_id": instance.access_rule.id
            }}
        )
        return response

    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "portal_access_rules",
            {"portal_access_rules": {
                "portal_id": instance.portal_id,
                "access_rule_id": instance.access_rule.id
            }}
        )
        return response

    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import PortalAccessRule, AccessRule
            
            catraca_objects = self.load_objects("portal_access_rules")

            with transaction.atomic():
                PortalAccessRule.objects.all().delete()
                for data in catraca_objects:
                    access_rule = AccessRule.objects.get(id=data["access_rule_id"])
                    PortalAccessRule.objects.create(
                        portal_id=data["portal_id"],
                        access_rule=access_rule
                    )

            return Response({
                "success": True,
                "message": f"Sincronizadas {len(catraca_objects)} associações regra-portal"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

class TemplateSyncMixin(CatracaSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("templates", [{
            "id": instance.id,
            "user_id": instance.user.id,
            "template": instance.template,
            "finger_type": 0,  # dedo comum
            "finger_position": 0  # campo reservado
        }])
        return response

    def update_in_catraca(self, instance):
        response = self.update_objects(
            "templates",
            [{
                "id": instance.id,
                "user_id": instance.user.id,
                "template": instance.template,
                "finger_type": 0,  # dedo comum
                "finger_position": 0  # campo reservado
            }],
            {"templates": {"id": instance.id}}
        )
        return response

    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "templates",
            {"templates": {"id": instance.id}}
        )
        return response

    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import Template
            from src.core.user.infra.user_django_app.models import User
            
            catraca_objects = self.load_objects(
                "templates",
                fields=["id", "user_id", "template", "finger_type", "finger_position"]
            )

            with transaction.atomic():
                Template.objects.all().delete()
                for data in catraca_objects:
                    Template.objects.create(
                        id=data["id"],
                        user_id=data["user_id"],
                        template=data["template"]
                    )

            return Response({
                "success": True,
                "message": f"Sincronizados {len(catraca_objects)} templates"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class PortalSyncMixin(CatracaSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("portals", [{
            "id": instance.id,
            "name": instance.name
        }])
        return response
    
    def update_in_catraca(self, instance):
        response = self.update_objects(
            "portals",
            [{
                "id": instance.id,
                "name": instance.name
            }],
            {"portals": {"id": instance.id}}
        )
        return response
    
    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "portals",
            {"portals": {"id": instance.id}}
        )
        return response
    
    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import Portal
            
            catraca_objects = self.load_objects("portals")

            with transaction.atomic():
                Portal.objects.all().delete()
                for data in catraca_objects:
                    Portal.objects.create(**data)

            return Response({
                "success": True,
                "message": f"Sincronizados {len(catraca_objects)} portais"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
        
class CardSyncMixin(CatracaSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("cards", [{
            "id": instance.id,
            "value": instance.value
        }])
        return response
    
    def update_in_catraca(self, instance):
        response = self.update_objects(
            "cards",
            [{
                "id": instance.id,
                "value": instance.value
            }],
            {"cards": {"id": instance.id}}
        )
        return response
    
    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "cards",
            {"cards": {"id": instance.id}}
        )
        return response
    
    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import Card
            from src.core.user.infra.user_django_app.models import User
            
            catraca_objects = self.load_objects("cards")
            
            with transaction.atomic():
                Card.objects.all().delete()
                for data in catraca_objects:
                    Card.objects.create(
                        id=data["id"],
                        value=data["value"]
                    )

            return Response({
                "success": True,
                "message": f"Sincronizados {len(catraca_objects)} cards"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        