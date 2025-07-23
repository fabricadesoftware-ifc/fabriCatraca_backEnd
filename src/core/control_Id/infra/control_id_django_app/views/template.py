from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction

from src.core.control_Id.infra.control_id_django_app.models.template import Template
from src.core.control_Id.infra.control_id_django_app.serializers.template import TemplateSerializer
from src.core.control_Id.infra.control_id_django_app.sync_mixins import TemplateSyncMixin
from src.core.control_Id.infra.control_id_django_app.models.device import Device

class TemplateViewSet(TemplateSyncMixin, viewsets.ModelViewSet):
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer

    def create(self, request, *args, **kwargs):
        """
        Cria um template biométrico.
        Parâmetros:
            enrollment_device_id: ID da catraca para fazer o cadastro (obrigatório)
        """
        enrollment_device_id = request.data.get('enrollment_device_id')
        
        if not enrollment_device_id:
            return Response({
                "error": "É necessário especificar uma catraca para cadastro (enrollment_device_id)"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Define a catraca para cadastro
            enrollment_device = Device.objects.get(id=enrollment_device_id)
            self.set_device(enrollment_device)
            
            # Primeiro cria no banco para ter o ID
            serializer = self.get_serializer(data={
                "user": request.data.get('user'),
                "enrollment_device_id": enrollment_device_id
            })
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            
            # Faz o cadastro remoto
            response = self.remote_enroll(
                user_id=instance.user.id,
                type="biometry",
                save=False,  # Não salvar na catraca ainda
                sync=True
            )
            
            if response.status_code != status.HTTP_201_CREATED:
                instance.delete()  # Remove do banco se falhar na catraca
                return Response({
                    "error": "Erro no cadastro remoto",
                    "details": response.data
                }, status=response.status_code)
                
            template_data = response.data  # Usa .data em vez de .json()
            
            with transaction.atomic():
                # Atualiza o template com os dados da catraca
                instance.template = template_data["template"]
                instance.save()
                
                # Cadastra em todas as catracas ativas
                devices = Device.objects.filter(is_active=True)
                
                for device in devices:
                    self.set_device(device)
                    
                    create_response = self.create_objects("templates", [{
                        "id": instance.id,
                        "user_id": instance.user.id,
                        "template": instance.template
                    }])
                    
                    if create_response.status_code != status.HTTP_201_CREATED:
                        # Se falhar em alguma catraca, reverte tudo
                        instance.delete()
                        return Response({
                            "error": f"Erro ao criar template na catraca {device.name}",
                            "details": create_response.data
                        }, status=create_response.status_code)
                    
                    # Adiciona a relação com a catraca
                    instance.devices.add(device)
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
        except Device.DoesNotExist:
            return Response({
                "error": f"Catraca com ID {enrollment_device_id} não encontrada"
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "error": "Erro ao processar template",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            # Atualiza o template no banco
            instance = serializer.save()
            
            # Atualiza em todas as catracas ativas
            devices = Device.objects.filter(is_active=True)
            
            for device in devices:
                self.set_device(device)
                response = self.update_objects(
                    "templates",
                    [{
                        "id": instance.id,
                        "user_id": instance.user.id,
                        "template": instance.template
                    }],
                    {"templates": {"id": instance.id}}
                )
                if response.status_code != status.HTTP_200_OK:
                    return Response({
                        "error": f"Erro ao atualizar template na catraca {device.name}",
                        "details": response.data
                    }, status=response.status_code)
                
                # Atualiza a relação com a catraca
                instance.devices.add(device)
        
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        with transaction.atomic():
            # Remove de todas as catracas ativas
            devices = Device.objects.filter(is_active=True)
            
            for device in devices:
                self.set_device(device)
                response = self.destroy_objects(
                    "templates",
                    {"templates": {"id": instance.id}}
                )
                if response.status_code != status.HTTP_204_NO_CONTENT:
                    return Response({
                        "error": f"Erro ao deletar template da catraca {device.name}",
                        "details": response.data
                    }, status=response.status_code)
            
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT) 