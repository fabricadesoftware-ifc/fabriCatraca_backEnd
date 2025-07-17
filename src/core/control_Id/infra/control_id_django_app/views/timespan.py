from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models.timespan import TimeSpan
from ..serializers.timespan import TimeSpanSerializer
from ..sync_mixins.timespan import TimeSpanSyncMixin

class TimeSpanViewSet(TimeSpanSyncMixin, viewsets.ModelViewSet):
    queryset = TimeSpan.objects.all()
    serializer_class = TimeSpanSerializer
    filterset_fields = ['id', 'time_zone', 'start', 'end']
    search_fields = ['time_zone__name']
    ordering_fields = ['id', 'start', 'end']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Criar na catraca
        response = self.create_objects("time_spans", [{
            "id": instance.id,
            "time_zone_id": instance.time_zone_id,
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
        response = self.update_objects(
            "time_spans",
            [{
                "id": instance.id,
                "time_zone_id": instance.time_zone_id,
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

        if response.status_code != status.HTTP_200_OK:
            return response

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Deletar na catraca
        response = self.destroy_objects(
            "time_spans",
            {"time_spans": {"id": instance.id}}
        )

        if response.status_code != status.HTTP_204_NO_CONTENT:
            return response

        # Deletar no banco local
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
                TimeSpan.objects.create(**data)

            return Response({
                "success": True,
                "message": f"Sincronizados {len(catraca_objects)} intervalos de tempo"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 