from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models import Template
from ..serializers import TemplateSerializer
from ..sync_mixins import TemplateSyncMixin

class TemplateViewSet(TemplateSyncMixin, viewsets.ModelViewSet):
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    filterset_fields = ['id', 'user']
    search_fields = ['user__name']
    ordering_fields = ['id', 'user']

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        try:
            # Garantir que a sessão está inicializada
            self.login()

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            # Cadastro remoto da biometria
            response = self.remote_enroll(
                user_id=instance.user_id,
                type="biometry",
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
            template_response = self.create_objects("templates", [{
                "user_id": instance.user_id,
                "template": data["template"],
                "finger_type": data.get("finger_type", 0),
                "finger_position": data.get("finger_position", 0)
            }])

            if not template_response.ok:
                instance.delete()
                return Response({
                    "error": "Erro ao salvar template",
                    "details": template_response.json() if template_response.content else str(template_response)
                }, status=template_response.status_code)

            # Atualizar o template no banco local
            instance.template = data["template"]
            instance.finger_type = data.get("finger_type", 0)
            instance.finger_position = data.get("finger_position", 0)
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
        response = self.session.post(
            f"{self.base_url}/modify_objects.fcgi",
            json={
                "templates": [{
                    "id": instance.id,
                    "user_id": instance.user_id,
                    "template": instance.template,
                    "finger_type": instance.finger_type,
                    "finger_position": instance.finger_position
                }],
                "where": {
                    "templates": {"id": instance.id}
                }
            }
        )

        if response.status_code != status.HTTP_200_OK:
            return Response({"error": response.text}, status=response.status_code)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()

            # Garantir que a sessão está inicializada
            self.login()

            # Deletar na catraca
            response = self.destroy_objects("templates", {"templates": {"id": instance.id}})

            if response.status_code != status.HTTP_204_NO_CONTENT:
                error_data = {}
                try:
                    if hasattr(response, 'data'):
                        error_data = response.data
                    elif hasattr(response, 'json'):
                        error_data = response.json()
                except:
                    error_data = {"message": "Erro ao deletar template na catraca"}

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
                "templates",
                fields=["id", "user_id", "template", "finger_type", "finger_position"],
                order_by=["id"]
            )

            # Apagar todos do banco local
            Template.objects.all().delete()

            # Cadastrar da catraca no banco local
            for data in catraca_objects:
                Template.objects.create(
                    id=data["id"],
                    user_id=data["user_id"],
                    template=data["template"],
                    finger_type=data.get("finger_type", 0),
                    finger_position=data.get("finger_position", 0)
                )

            return Response({
                "success": True,
                "message": f"Sincronizados {len(catraca_objects)} templates"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 