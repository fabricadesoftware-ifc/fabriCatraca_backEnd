from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db import transaction
from drf_spectacular.utils import extend_schema

from src.core.control_Id.infra.control_id_django_app.models.template import Template
from src.core.control_Id.infra.control_id_django_app.serializers.template import TemplateSerializer
from src.core.__seedwork__.infra.mixins import TemplateSyncMixin
from src.core.control_Id.infra.control_id_django_app.models.device import Device

@extend_schema(tags=["Templates"]) 
class TemplateViewSet(TemplateSyncMixin, viewsets.ModelViewSet):
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    filterset_fields = ['user']

    def create(self, request, *args, **kwargs):
        """
        Cria um template biométrico.
        Fluxo:
        1. Valida dados de entrada (user_id, device_id)
        2. Realiza cadastro remoto na catraca (remote_enroll)
        3. Salva no banco de dados com o template retornado
        4. Replica para outras catracas
        """
        try:
            enrollment_device_id = request.data.get('enrollment_device_id')
            if not enrollment_device_id:
                return Response({
                    "error": "É necessário especificar uma catraca para cadastro (enrollment_device_id)"
                }, status=status.HTTP_400_BAD_REQUEST)

            user_id = request.data.get('user_id') or request.query_params.get('user_id') or request.data.get('user')
            if not user_id:
                return Response({
                    "error": "Usuário (user_id) é obrigatório"
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                enrollment_device = Device.objects.get(id=enrollment_device_id)
                self.set_device(enrollment_device)
            except Device.DoesNotExist:
                return Response({
                    "error": f"Catraca com ID {enrollment_device_id} não encontrada"
                }, status=status.HTTP_404_NOT_FOUND)

            response = self.remote_enroll(
                user_id=user_id,
                type="biometry",
                save=False,
                sync=True
            )
            
            if response.status_code != status.HTTP_201_CREATED:
                return Response({
                    "error": "Erro no cadastro remoto da biometria",
                    "details": response.data
                }, status=response.status_code)

            template_data = response.data
            captured_template = template_data.get("template")

            if not captured_template:
                 return Response({
                    "error": "Catraca não retornou o template biométrico",
                    "details": template_data
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            with transaction.atomic():
                data = {
                    "user_id": user_id,
                    "enrollment_device_id": enrollment_device_id,
                }

                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)

                instance = serializer.save(template=captured_template)
                
                devices = Device.objects.filter(is_active=True)
                
                errors = []
                for device in devices:
                    self.set_device(device)
                    create_response = self.create_objects("templates", [{
                        "id": instance.id,
                        "user_id": instance.user.id,
                        "template": instance.template
                    }])
                    
                    if create_response.status_code != status.HTTP_201_CREATED:
                        errors.append(f"{device.name}: {create_response.data}")
                    else:
                        instance.devices.add(device)
                
                if errors:
                    print(f"Erros de replicação: {errors}")
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            import traceback
            traceback.print_exc() # Log no console para debug
            return Response({
                "error": "Erro interno no servidor ao processar biometria",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            instance = serializer.save()
            
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
                
                instance.devices.add(device)
        
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        with transaction.atomic():
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