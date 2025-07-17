from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Template, TimeZone, TimeSpan, AccessRule, UserAccessRule, AccessRuleTimeZone, PortalAccessRule, Portal
from .serializers import TemplateSerializer, TimeZoneSerializer, TimeSpanSerializer, AccessRuleSerializer, UserAccessRuleSerializer, AccessRuleTimeZoneSerializer, PortalAccessRuleSerializer, PortalSerializer
from src.core.user.infra.user_django_app.models import User
from src.core.user.infra.user_django_app.serializers import UserSerializer
from src.core.user.infra.user_django_app.views import UserViewSet
from django.db import transaction
from src.core.seedwork.infra.sync_mixins import (
    TimeZoneSyncMixin, TimeSpanSyncMixin, AccessRuleSyncMixin,
    UserAccessRuleSyncMixin, AccessRuleTimeZoneSyncMixin, PortalAccessRuleSyncMixin,
    TemplateSyncMixin, PortalSyncMixin
)

class TemplateViewSet(TemplateSyncMixin, viewsets.ModelViewSet):
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    filterset_fields = ['id', 'user']
    search_fields = ['user__name']
    ordering_fields = ['id', 'user']

    @action(detail=False, methods=['get'])
    def sync(self, request):
        return self.sync_from_catraca()

class TimeZoneViewSet(TimeZoneSyncMixin, viewsets.ModelViewSet):
    queryset = TimeZone.objects.all()
    serializer_class = TimeZoneSerializer
    filterset_fields = ['id', 'name']
    search_fields = ['name']
    ordering_fields = ['id', 'name']

    @action(detail=False, methods=['get'])
    def sync(self, request):
        return self.sync_from_catraca()

class TimeSpanViewSet(TimeSpanSyncMixin, viewsets.ModelViewSet):
    queryset = TimeSpan.objects.all()
    serializer_class = TimeSpanSerializer
    filterset_fields = ['id', 'time_zone', 'start', 'end']
    search_fields = ['time_zone__name']
    ordering_fields = ['id', 'start', 'end']

    @action(detail=False, methods=['get'])
    def sync(self, request):
        return self.sync_from_catraca()

class AccessRuleViewSet(AccessRuleSyncMixin, viewsets.ModelViewSet):
    queryset = AccessRule.objects.all()
    serializer_class = AccessRuleSerializer
    filterset_fields = ['id', 'name', 'type', 'priority']
    search_fields = ['name']
    ordering_fields = ['id', 'name', 'priority']

    @action(detail=False, methods=['get'])
    def sync(self, request):
        return self.sync_from_catraca()

class UserAccessRuleViewSet(UserAccessRuleSyncMixin, viewsets.ModelViewSet):
    queryset = UserAccessRule.objects.all()
    serializer_class = UserAccessRuleSerializer
    filterset_fields = ['user', 'access_rule']
    search_fields = ['user', 'access_rule']
    ordering_fields = ['user', 'access_rule']

    @action(detail=False, methods=['get'])
    def sync(self, request):
        return self.sync_from_catraca()

class AccessRuleTimeZoneViewSet(AccessRuleTimeZoneSyncMixin, viewsets.ModelViewSet):
    queryset = AccessRuleTimeZone.objects.all()
    serializer_class = AccessRuleTimeZoneSerializer
    filterset_fields = ['access_rule', 'time_zone']
    search_fields = ['access_rule', 'time_zone']
    ordering_fields = ['access_rule', 'time_zone']

    @action(detail=False, methods=['get'])
    def sync(self, request):
        return self.sync_from_catraca()

class PortalViewSet(PortalSyncMixin, viewsets.ModelViewSet):
    queryset = Portal.objects.all()
    serializer_class = PortalSerializer
    filterset_fields = ['id', 'name']
    search_fields = ['name']
    ordering_fields = ['id', 'name']

    @action(detail=False, methods=['get'])
    def sync(self, request):
        return self.sync_from_catraca()

class PortalAccessRuleViewSet(PortalAccessRuleSyncMixin, viewsets.ModelViewSet):
    queryset = PortalAccessRule.objects.all()
    serializer_class = PortalAccessRuleSerializer
    filterset_fields = ['portal', 'access_rule']
    search_fields = ['access_rule']
    ordering_fields = ['portal', 'access_rule']

    @action(detail=False, methods=['get'])
    def sync(self, request):
        return self.sync_from_catraca()

class CatracaViewSet(viewsets.ViewSet):
    """
    API endpoint para operações gerais da catraca.
    """

    @action(detail=False, methods=['get'])
    def sync_all(self, request):
        """Sincroniza todos os objetos da catraca"""
        try:
            # Sincronizar templates
            template_viewset = TemplateViewSet()
            template_response = template_viewset.sync(request)
            if template_response.status_code != status.HTTP_200_OK:
                return template_response

            # Sincronizar usuários
            user_viewset = UserViewSet()
            user_response = user_viewset.sync(request)
            if user_response.status_code != status.HTTP_200_OK:
                return user_response

            # Sincronizar zonas de tempo
            timezone_viewset = TimeZoneViewSet()
            timezone_response = timezone_viewset.sync(request)
            if timezone_response.status_code != status.HTTP_200_OK:
                return timezone_response

            # Sincronizar intervalos de tempo
            timespan_viewset = TimeSpanViewSet()
            timespan_response = timespan_viewset.sync(request)
            if timespan_response.status_code != status.HTTP_200_OK:
                return timespan_response

            # Sincronizar regras de acesso
            accessrule_viewset = AccessRuleViewSet()
            accessrule_response = accessrule_viewset.sync(request)
            if accessrule_response.status_code != status.HTTP_200_OK:
                return accessrule_response

            # Sincronizar associações usuário-regra
            user_accessrule_viewset = UserAccessRuleViewSet()
            user_accessrule_response = user_accessrule_viewset.sync(request)
            if user_accessrule_response.status_code != status.HTTP_200_OK:
                return user_accessrule_response

            # Sincronizar associações regra-zona
            accessrule_timezone_viewset = AccessRuleTimeZoneViewSet()
            accessrule_timezone_response = accessrule_timezone_viewset.sync(request)
            if accessrule_timezone_response.status_code != status.HTTP_200_OK:
                return accessrule_timezone_response

            # Sincronizar associações regra-portal
            portal_accessrule_viewset = PortalAccessRuleViewSet()
            portal_accessrule_response = portal_accessrule_viewset.sync(request)
            if portal_accessrule_response.status_code != status.HTTP_204_NO_CONTENT:
                return portal_accessrule_response

            return Response({
                "success": True,
                "message": "Todos os objetos foram sincronizados com sucesso"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)