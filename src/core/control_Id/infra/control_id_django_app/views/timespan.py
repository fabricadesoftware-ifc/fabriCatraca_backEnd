from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db import transaction
from rest_framework.decorators import action

from ..models.timespan import TimeSpan
from ..serializers.timespan import TimeSpanSerializer
from src.core.__seedwork__.infra.mixins import TimeSpanSyncMixin
from ..models.device import Device
from drf_spectacular.utils import extend_schema

@extend_schema(tags=["Time Spans"]) 
class TimeSpanViewSet(TimeSpanSyncMixin, viewsets.ModelViewSet):
    queryset = TimeSpan.objects.all()
    serializer_class = TimeSpanSerializer
    filterset_fields = ['id', 'time_zone', 'start', 'end']
    search_fields = ['time_zone__name']
    ordering_fields = ['id', 'start', 'end']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            # Primeiro cria no banco
            instance = serializer.save()
            
            # Depois replica para todas as catracas ativas
            devices = Device.objects.filter(is_active=True)
            if not devices:
                instance.delete()
                return Response({
                    "error": "Nenhuma catraca ativa encontrada"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            for device in devices:
                self.set_device(device)
                response = self.create_objects("time_spans", [{
                    "id": instance.id,
                    "time_zone_id": instance.time_zone_id,
                    "start": instance.start,
                    "end": instance.end,
                    "sun": 1 if instance.sun else 0,
                    "mon": 1 if instance.mon else 0,
                    "tue": 1 if instance.tue else 0,
                    "wed": 1 if instance.wed else 0,
                    "thu": 1 if instance.thu else 0,
                    "fri": 1 if instance.fri else 0,
                    "sat": 1 if instance.sat else 0,
                    "hol1": 1 if instance.hol1 else 0,
                    "hol2": 1 if instance.hol2 else 0,
                    "hol3": 1 if instance.hol3 else 0
                }])
                
                if response.status_code != status.HTTP_201_CREATED:
                    instance.delete()
                    return Response({
                        "error": f"Erro ao criar intervalo de tempo na catraca {device.name}",
                        "details": response.data
                    }, status=response.status_code)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            # Primeiro atualiza no banco
            instance = serializer.save()
            
            # Depois atualiza em todas as catracas ativas
            devices = Device.objects.filter(is_active=True)
            
            for device in devices:
                self.set_device(device)
                response = self.update_objects(
                    "time_spans",
                    {
                        "id": instance.id,
                        "time_zone_id": instance.time_zone_id,
                        "start": instance.start,
                        "end": instance.end,
                        "sun": 1 if instance.sun else 0,
                        "mon": 1 if instance.mon else 0,
                        "tue": 1 if instance.tue else 0,
                        "wed": 1 if instance.wed else 0,
                        "thu": 1 if instance.thu else 0,
                        "fri": 1 if instance.fri else 0,
                        "sat": 1 if instance.sat else 0,
                        "hol1": 1 if instance.hol1 else 0,
                        "hol2": 1 if instance.hol2 else 0,
                        "hol3": 1 if instance.hol3 else 0
                    },
                    {"time_spans": {"id": instance.id}}
                )
                
                if response.status_code != status.HTTP_200_OK:
                    return Response({
                        "error": f"Erro ao atualizar intervalo de tempo na catraca {device.name}",
                        "details": response.data
                    }, status=response.status_code)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        with transaction.atomic():
            # Remove de todas as catracas ativas
            devices = Device.objects.filter(is_active=True)
            
            for device in devices:
                self.set_device(device)
                response = self.destroy_objects(
                    "time_spans",
                    {"time_spans": {"id": instance.id}}
                )
                
                if response.status_code != status.HTTP_204_NO_CONTENT:
                    return Response({
                        "error": f"Erro ao deletar intervalo de tempo da catraca {device.name}",
                        "details": response.data
                    }, status=response.status_code)

            # Se removeu de todas as catracas, remove do banco
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def sync(self, request):
        try:
            # Carregar da catraca
            catraca_objects = self.load_objects(
                "time_spans",
                fields=["id", "time_zone_id", "start", "end", "sun", "mon", "tue", "wed", "thu", "fri", "sat", "hol1", "hol2", "hol3"],
                order_by=["id"]
            )

            # Apagar todos do banco local
            TimeSpan.objects.all().delete()

            # Cadastrar da catraca no banco local
            for data in catraca_objects:
                # Converte inteiros para booleanos
                data['sun'] = bool(data.get('sun', 0))
                data['mon'] = bool(data.get('mon', 0))
                data['tue'] = bool(data.get('tue', 0))
                data['wed'] = bool(data.get('wed', 0))
                data['thu'] = bool(data.get('thu', 0))
                data['fri'] = bool(data.get('fri', 0))
                data['sat'] = bool(data.get('sat', 0))
                data['hol1'] = bool(data.get('hol1', 0))
                data['hol2'] = bool(data.get('hol2', 0))
                data['hol3'] = bool(data.get('hol3', 0))
                
                TimeSpan.objects.create(**data)

            return Response({
                "success": True,
                "message": f"Sincronizados {len(catraca_objects)} intervalos de tempo"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 