from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from datetime import datetime, timedelta
from django.utils import timezone
from src.core.control_Id.infra.control_id_django_app.models import AccessLogs
from src.core.control_Id.infra.control_id_django_app.serializers import AccessLogsSerializer
from src.core.__seedwork__.infra.mixins import AccessLogsSyncMixin

from rest_framework.pagination import PageNumberPagination

class AccessLogsPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000

@extend_schema(tags=["Access Logs"])
class AccessLogsViewSet(AccessLogsSyncMixin, viewsets.ModelViewSet):
    queryset = AccessLogs.objects.select_related('device', 'user', 'portal', 'access_rule').all()
    serializer_class = AccessLogsSerializer
    pagination_class = AccessLogsPagination
    filterset_fields = ['id', 'time', 'event_type', 'device', 'identifier_id', 'user', 'portal', 'access_rule']
    search_fields = ['device__name', 'user__name', 'portal__name', 'identifier_id']
    ordering_fields = ['id', 'time', 'event_type']
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        # Criar na catraca
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
        
        if response.status_code != status.HTTP_201_CREATED:
            instance.delete()  # Reverte se falhar na catraca
            return response
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        # Atualizar na catraca
        response = self.update_objects("access_logs", {
            "id": instance.id,
            "time": instance.time,
            "event": instance.event_type,
            "device": instance.device,
            "identifier_id": instance.identifier_id,
            "user": instance.user,
            "portal": instance.portal,
            "access_rule": instance.access_rule,
        }, {"access_logs": {"id": instance.id}})
        
        if response.status_code != status.HTTP_201_CREATED:
            instance.delete()  # Reverte se falhar na catraca
            return response
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Deletar na catraca
        response = self.destroy_objects("access_logs", {"access_logs": {"id": instance.id}})
        
        if response.status_code != status.HTTP_204_NO_CONTENT:
            return response
        
        # Deletar no banco local
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def list_all_by_type(self, request):
        event_type = request.query_params.get('event_type', None)
        
        # Usa o queryset base que já tem select_related
        logs = self.get_queryset()
        
        if event_type is not None:
            logs = logs.filter(event_type=event_type)
        
        # Aplica paginação
        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    @extend_schema(
        parameters=[
            {
                "name": "days",
                "in": "query",
                "required": True,
                "schema": {"type": "integer", "minimum": 1},
                "description": "Número de dias para filtrar os logs (ex: 15, 30, 60)"
            },
            {
                "name": "event_type",
                "in": "query",
                "required": False,
                "schema": {"type": "integer"},
                "description": "Tipo de evento opcional para filtrar"
            }
        ],
        responses={200: AccessLogsSerializer(many=True)}
    )
    def logs_by_days(self, request):
        """
        Retorna logs de acesso dos últimos N dias.
        Exemplo: /api/access-logs/logs_by_days/?days=15
        """
        try:
            days = int(request.query_params.get('days', 30))
            if days <= 0:
                return Response(
                    {"error": "O parâmetro 'days' deve ser um número positivo"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Calcular a data de início (hoje - N dias)
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            # Usa o queryset base que já tem select_related
            logs = self.get_queryset().filter(
                time__gte=start_date,
                time__lte=end_date
            )
            
            # Filtro opcional por tipo de evento
            event_type = request.query_params.get('event_type', None)
            if event_type is not None:
                try:
                    event_type = int(event_type)
                    logs = logs.filter(event_type=event_type)
                except ValueError:
                    return Response(
                        {"error": "O parâmetro 'event_type' deve ser um número válido"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Aplica paginação
            page = self.paginate_queryset(logs)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(logs, many=True)
            return Response(serializer.data)
            
        except ValueError:
            return Response(
                {"error": "O parâmetro 'days' deve ser um número válido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Erro interno: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )