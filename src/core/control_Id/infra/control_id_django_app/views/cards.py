from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from src.core.control_Id.infra.control_id_django_app.models.cards import Card
from src.core.control_Id.infra.control_id_django_app.serializers.cards import CardSerializer
from src.core.control_Id.infra.control_id_django_app.sync_mixins import CardSyncMixin

class CardViewSet(CardSyncMixin, viewsets.ModelViewSet):
    queryset = Card.objects.all()
    serializer_class = CardSerializer
    filterset_fields = ['id', 'value', 'user']
    search_fields = ['value', 'user__name']
    ordering_fields = ['id', 'value', 'user']
    
    def create(self, request, *args, **kwargs):
        try:
            # Garantir que a sessão está inicializada
            self.login()

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            # Cadastro remoto de rfid
            response = self.remote_enroll(
                user_id=instance.user_id,
                type="card",
                save=False,  # Não salvar na catraca ainda
                sync=True
            )

            if not response.ok:
                instance.delete()  # Reverte se falhar
                return Response({
                    "error": "Erro no cadastro remoto",
                    "details": response.json() if response.content else str(response)
                }, status=response.status_code)

            try:
                data = response.json()
            except ValueError:
                instance.delete()
                return Response({
                    "error": "Resposta inválida da catraca",
                    "details": response.content.decode() if response.content else None
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Criar template na catraca
            template_response = self.create_objects("cards", [{
                "user_id": instance.user_id,
                "value": data["value"],
            }])

            if not template_response.ok:
                instance.delete()
                return Response({
                    "error": "Erro ao salvar card",
                    "details": template_response.json() if template_response.content else str(template_response)
                }, status=template_response.status_code)

            # Atualizar o template no banco local
            instance.value = data["value"]
            instance.save()

            return Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)

        except Exception as e:
            if 'instance' in locals():
                instance.delete()
            return Response({
                "error": "Erro interno",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Atualizar na catraca
        response = self.update_objects("cards", [{
            "id": instance.id,
            "user_id": instance.user_id,
            "value": instance.value
        }], {"id": instance.id})


        if response.status_code != status.HTTP_200_OK:
            return Response({"error": response.text}, status=response.status_code)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()

            # Garantir que a sessão está inicializada
            self.login()

            # Deletar na catraca
            response = self.destroy_objects("cards", {"cards": {"id": instance.id}})

            if response.status_code != status.HTTP_204_NO_CONTENT:
                error_data = {}
                try:
                    if hasattr(response, 'data'):
                        error_data = response.data
                    elif hasattr(response, 'json'):
                        error_data = response.json()
                except:
                    error_data = {"message": "Erro ao deletar card na catraca"}

                return Response(error_data, status=response.status_code)

            # Deletar no banco local
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return Response({
                "error": "Erro interno",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def sync(self, request):
        try:
            # Carregar da catraca
            catraca_objects = self.load_objects(
                "cards",
                fields=["id", "user_id", "value"],
                order_by=["id"]
            )

            # Apagar todos do banco local
            Card.objects.all().delete()

            # Cadastrar da catraca no banco local
            for data in catraca_objects:
                Card.objects.create(
                    id=data["id"],
                    user_id=data["user_id"],
                    value=data["value"]
                )

            return Response({
                "success": True,
                "message": f"Sincronizados {len(catraca_objects)} cards"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 