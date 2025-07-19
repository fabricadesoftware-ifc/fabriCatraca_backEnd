from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction

from src.core.control_Id.infra.control_id_django_app.models.cards import Card
from src.core.control_Id.infra.control_id_django_app.serializers.cards import CardSerializer
from src.core.control_Id.infra.control_id_django_app.sync_mixins import CardSyncMixin
from src.core.control_Id.infra.control_id_django_app.models.device import Device

class CardViewSet(CardSyncMixin, viewsets.ModelViewSet):
    queryset = Card.objects.all()
    serializer_class = CardSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Cria um cartão.
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
                "user": request.data.get('user')
            })
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()

            # Faz o cadastro remoto
            response = self.remote_enroll(
                user_id=instance.user.id,
                type="card",
                save=False,  # Não salvar na catraca ainda
                sync=True
            )

            if response.status_code != status.HTTP_200_OK:
                instance.delete()  # Remove do banco se falhar na catraca
                return Response({
                    "error": "Erro no cadastro remoto",
                    "details": response.json() if response.content else str(response)
                }, status=response.status_code)

            card_data = response.json()
            
            with transaction.atomic():
                # Atualiza o cartão com os dados da catraca
                instance.value = card_data["value"]
                instance.save()
                
                # Cadastra em todas as catracas ativas
                devices = Device.objects.filter(is_active=True)
                
                for device in devices:
                    self.set_device(device)
                    
                    create_response = self.create_objects("cards", [{
                        "id": instance.id,
                        "user_id": instance.user.id,
                        "value": instance.value
                    }])

                    if create_response.status_code != status.HTTP_201_CREATED:
                        # Se falhar em alguma catraca, reverte tudo
                        instance.delete()
                        return Response({
                            "error": f"Erro ao criar cartão na catraca {device.name}",
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
                "error": "Erro ao processar cartão",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            # Atualiza o cartão no banco
            instance = serializer.save()
            
            # Atualiza em todas as catracas ativas
            devices = Device.objects.filter(is_active=True)
            
            for device in devices:
                self.set_device(device)
                response = self.update_objects(
                    "cards",
                    [{
                        "id": instance.id,
                        "user_id": instance.user.id,
                        "value": instance.value
                    }],
                    {"cards": {"id": instance.id}}
                )
                if response.status_code != status.HTTP_200_OK:
                    return Response({
                        "error": f"Erro ao atualizar cartão na catraca {device.name}",
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
                    "cards",
                    {"cards": {"id": instance.id}}
                )
                if response.status_code != status.HTTP_204_NO_CONTENT:
                    return Response({
                        "error": f"Erro ao deletar cartão da catraca {device.name}",
                        "details": response.data
                    }, status=response.status_code)

            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT) 