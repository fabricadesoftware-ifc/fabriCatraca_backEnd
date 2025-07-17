from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Template, TimeZone, TimeSpan, AccessRule, UserAccessRule, AccessRuleTimeZone, PortalAccessRule
from .serializers import TemplateSerializer, TimeZoneSerializer, TimeSpanSerializer, AccessRuleSerializer, UserAccessRuleSerializer, AccessRuleTimeZoneSerializer, PortalAccessRuleSerializer
from src.core.user.infra.user_django_app.models import User
from src.core.user.infra.user_django_app.serializers import UserSerializer
import requests
from django.conf import settings
from django.db import transaction

class CatracaViewSet(viewsets.ViewSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = None
        self.catraka_url = settings.CATRAKA_URL
        self.catraka_user = settings.CATRAKA_USER
        self.catraka_pass = settings.CATRAKA_PASS

    def login(self):
        if self.session:
            return self.session
        response = requests.post(f"{self.catraka_url}/login.fcgi", json={
            "login": self.catraka_user,
            "password": self.catraka_pass
        })
        response.raise_for_status()
        self.session = response.json().get("session")
        return self.session

    # Sincronização de todos os objetos
    @action(detail=False, methods=['post'])
    def sync(self, request):
        try:
            sess = self.login()

            # Carregar todos os objetos da catraca
            user_response = requests.post(f"{self.catraka_url}/load_objects.fcgi?session={sess}", json={
                "object": "users",
                "fields": ["id", "name", "registration"],
                "order_by": ["id"]
            })
            user_response.raise_for_status()
            catraca_users = user_response.json().get("users", [])

            template_response = requests.post(f"{self.catraka_url}/load_objects.fcgi?session={sess}", json={
                "object": "templates"
            })
            template_response.raise_for_status()
            catraca_templates = template_response.json().get("templates", [])

            timezone_response = requests.post(f"{self.catraka_url}/load_objects.fcgi?session={sess}", json={
                "object": "time_zones",
                "fields": ["id", "name"]
            })
            timezone_response.raise_for_status()
            catraca_timezones = timezone_response.json().get("time_zones", [])

            timespan_response = requests.post(f"{self.catraka_url}/load_objects.fcgi?session={sess}", json={
                "object": "time_spans"
            })
            timespan_response.raise_for_status()
            catraca_timespans = timespan_response.json().get("time_spans", [])

            accessrule_response = requests.post(f"{self.catraka_url}/load_objects.fcgi?session={sess}", json={
                "object": "access_rules"
            })
            accessrule_response.raise_for_status()
            catraca_accessrules = accessrule_response.json().get("access_rules", [])

            user_accessrule_response = requests.post(f"{self.catraka_url}/load_objects.fcgi?session={sess}", json={
                "object": "user_access_rules"
            })
            user_accessrule_response.raise_for_status()
            catraca_user_accessrules = user_accessrule_response.json().get("user_access_rules", [])

            accessrule_timezone_response = requests.post(f"{self.catraka_url}/load_objects.fcgi?session={sess}", json={
                "object": "access_rule_time_zones"
            })
            accessrule_timezone_response.raise_for_status()
            catraca_accessrule_timezones = accessrule_timezone_response.json().get("access_rule_time_zones", [])

            portal_accessrule_response = requests.post(f"{self.catraka_url}/load_objects.fcgi?session={sess}", json={
                "object": "portal_access_rules"
            })
            portal_accessrule_response.raise_for_status()
            catraca_portal_accessrules = portal_accessrule_response.json().get("portal_access_rules", [])

            # Apagar todos os dados locais
            with transaction.atomic():
                User.objects.all().delete()
                Template.objects.all().delete()
                TimeZone.objects.all().delete()
                TimeSpan.objects.all().delete()
                AccessRule.objects.all().delete()
                UserAccessRule.objects.all().delete()
                AccessRuleTimeZone.objects.all().delete()
                PortalAccessRule.objects.all().delete()

                # Cadastrar usuários
                for user_data in catraca_users:
                    User.objects.create(
                        id=user_data["id"],
                        name=user_data["name"],
                        registration=user_data.get("registration", "")
                    )

                # Cadastrar biometrias
                for template_data in catraca_templates:
                    user = User.objects.get(id=template_data["user_id"])
                    Template.objects.create(
                        id=template_data["id"],
                        user=user,
                        template=template_data["template"]
                    )

                # Cadastrar zonas de tempo
                for timezone_data in catraca_timezones:
                    TimeZone.objects.create(
                        id=timezone_data["id"],
                        name=timezone_data["name"]
                    )

                # Cadastrar intervalos de tempo
                for timespan_data in catraca_timespans:
                    time_zone = TimeZone.objects.get(id=timespan_data["time_zone_id"])
                    TimeSpan.objects.create(
                        id=timespan_data["id"],
                        time_zone=time_zone,
                        start=timespan_data["start"],
                        end=timespan_data["end"],
                        sun=timespan_data.get("sun", False),
                        mon=timespan_data.get("mon", False),
                        tue=timespan_data.get("tue", False),
                        wed=timespan_data.get("wed", False),
                        thu=timespan_data.get("thu", False),
                        fri=timespan_data.get("fri", False),
                        sat=timespan_data.get("sat", False),
                        hol1=timespan_data.get("hol1", False),
                        hol2=timespan_data.get("hol2", False),
                        hol3=timespan_data.get("hol3", False)
                    )

                # Cadastrar regras de acesso
                for accessrule_data in catraca_accessrules:
                    AccessRule.objects.create(
                        id=accessrule_data["id"],
                        name=accessrule_data["name"],
                        type=accessrule_data["type"],
                        priority=accessrule_data["priority"]
                    )

                # Cadastrar associações usuário-regra
                for uar_data in catraca_user_accessrules:
                    user = User.objects.get(id=uar_data["user_id"])
                    access_rule = AccessRule.objects.get(id=uar_data["access_rule_id"])
                    UserAccessRule.objects.create(
                        user=user,
                        access_rule=access_rule
                    )

                # Cadastrar associações regra-zona de tempo
                for art_data in catraca_accessrule_timezones:
                    access_rule = AccessRule.objects.get(id=art_data["access_rule_id"])
                    time_zone = TimeZone.objects.get(id=art_data["time_zone_id"])
                    AccessRuleTimeZone.objects.create(
                        access_rule=access_rule,
                        time_zone=time_zone
                    )

                # Cadastrar associações regra-portal
                for par_data in catraca_portal_accessrules:
                    access_rule = AccessRule.objects.get(id=par_data["access_rule_id"])
                    PortalAccessRule.objects.create(
                        portal_id=par_data["portal_id"],
                        access_rule=access_rule
                    )

            return Response({
                "success": True,
                "message": f"Sincronizados {len(catraca_users)} usuários, {len(catraca_templates)} biometrias, "
                           f"{len(catraca_timezones)} zonas de tempo, {len(catraca_timespans)} intervalos, "
                           f"{len(catraca_accessrules)} regras, {len(catraca_user_accessrules)} associações usuário-regra, "
                           f"{len(catraca_accessrule_timezones)} associações regra-zona, {len(catraca_portal_accessrules)} associações regra-portal"
            })
        except requests.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)