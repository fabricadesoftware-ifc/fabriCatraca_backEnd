from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.response import Response

from src.core.__seedwork__.infra.mixins import CardSyncMixin
from src.core.control_id.infra.control_id_django_app.models.cards import Card
from src.core.control_id.infra.control_id_django_app.models.device import Device
from src.core.control_id.infra.control_id_django_app.serializers.cards import (
    CardSerializer,
)
from src.core.user.infra.user_django_app.models import User


@extend_schema(tags=["Cards"])
class CardViewSet(CardSyncMixin, viewsets.ModelViewSet):
    queryset = Card.objects.all()
    serializer_class = CardSerializer
    filterset_fields = ["id", "user", "value"]
    search_fields = ["value", "user__name", "user__id", "user__registration"]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Compatibilidade com clientes que ainda enviam ?user_id=<id>
        user_id = self.request.query_params.get("user_id")
        if user_id not in (None, ""):
            queryset = queryset.filter(user_id=user_id)

        return queryset

    @staticmethod
    def _card_value_as_int(value):
        return int(value) if value not in (None, "") else value

    @staticmethod
    def _user_payload(user):
        payload = {
            "id": user.id,
            "name": user.name,
            "registration": user.registration or "",
        }
        return payload

    def _ensure_user_on_device(self, device, user):
        self.set_device(device)
        try:
            create_response = self.create_objects(
                "users",
                [self._user_payload(user)],
            )
            if create_response.status_code == status.HTTP_201_CREATED:
                return True
        except Exception:
            pass

        try:
            update_response = self.update_objects(
                "users",
                {
                    "name": user.name,
                    "registration": user.registration or "",
                },
                {"users": {"id": user.id}},
            )
            return update_response.status_code == status.HTTP_200_OK
        except Exception:
            return False

    def _get_target_devices_for_user(self, user: User):
        return list(user.get_target_devices(include_inactive=False))

    def create(self, request, *args, **kwargs):
        """
        Cria um cartao por captura remota na catraca.

        Fluxo:
        1. valida user_id + enrollment_device_id
        2. executa remote_enroll na catraca escolhida
        3. salva no banco com o valor retornado
        4. replica para as demais catracas ativas
        """
        try:
            enrollment_device_id = request.data.get("enrollment_device_id")
            if not enrollment_device_id:
                return Response(
                    {
                        "error": (
                            "E necessario especificar uma catraca para cadastro "
                            "(enrollment_device_id)"
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user_id = (
                request.data.get("user_id")
                or request.query_params.get("user_id")
                or request.data.get("user")
            )
            if not user_id:
                return Response(
                    {"error": "Usuario (user_id) e obrigatorio"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                enrollment_device = Device.objects.get(id=enrollment_device_id)
                self.set_device(enrollment_device)
            except Device.DoesNotExist:
                return Response(
                    {
                        "error": (
                            f"Catraca com ID {enrollment_device_id} nao encontrada"
                        )
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            user = User.objects.get(id=int(user_id))
            target_device_ids = {
                device.id for device in self._get_target_devices_for_user(user)
            }
            if not target_device_ids:
                return Response(
                    {"error": "Usuario nao possui catracas alvo para cartao."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if enrollment_device.id not in target_device_ids:
                return Response(
                    {
                        "error": "A catraca escolhida nao faz parte do escopo do usuario."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            response = self.remote_enroll(
                user_id=user_id,
                type="card",
                save=False,
                sync=True,
            )

            if response.status_code != status.HTTP_201_CREATED:
                return Response(
                    {
                        "error": "Erro no cadastro remoto do cartao",
                        "details": response.data,
                    },
                    status=response.status_code,
                )

            card_data = response.data
            captured_value = card_data.get("card_value")
            if not captured_value:
                return Response(
                    {
                        "error": "Catraca nao retornou o valor do cartao",
                        "details": card_data,
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            with transaction.atomic():
                serializer = self.get_serializer(
                    data={
                        "user_id": user_id,
                        "enrollment_device_id": enrollment_device_id,
                    }
                )
                serializer.is_valid(raise_exception=True)

                instance = serializer.save(value=str(captured_value))
                card_value_int = self._card_value_as_int(captured_value)

                devices = self._get_target_devices_for_user(instance.user)
                errors = []
                for device in devices:
                    if not self._ensure_user_on_device(device, instance.user):
                        errors.append(
                            f"{device.name}: usuario {instance.user.id} ausente"
                        )
                        continue

                    try:
                        create_response = self.create_objects(
                            "cards",
                            [
                                {
                                    "id": instance.id,
                                    "user_id": instance.user.id,
                                    "value": card_value_int,
                                }
                            ],
                        )

                        if create_response.status_code != status.HTTP_201_CREATED:
                            errors.append(f"{device.name}: {create_response.data}")
                    except Exception as exc:
                        errors.append(f"{device.name}: {exc}")

                if errors:
                    print(f"Erros de replicacao de cartao: {errors}")

                return Response(
                    self.get_serializer(instance).data,
                    status=status.HTTP_201_CREATED,
                )

        except Exception as e:
            import traceback

            traceback.print_exc()
            return Response(
                {
                    "error": "Erro interno no servidor ao processar cartao",
                    "details": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            instance = serializer.save()

            devices = self._get_target_devices_for_user(instance.user)

            for device in devices:
                if not self._ensure_user_on_device(device, instance.user):
                    return Response(
                        {
                            "error": (
                                f"Usuario {instance.user.id} ausente na catraca "
                                f"{device.name}"
                            ),
                        },
                        status=status.HTTP_409_CONFLICT,
                    )
                response = self.update_objects(
                    "cards",
                    [
                        {
                            "id": instance.id,
                            "user_id": instance.user.id,
                            "value": self._card_value_as_int(instance.value),
                        }
                    ],
                    {"cards": {"id": instance.id}},
                )
                if response.status_code != status.HTTP_200_OK:
                    return Response(
                        {
                            "error": (
                                f"Erro ao atualizar cartao na catraca {device.name}"
                            ),
                            "details": response.data,
                        },
                        status=response.status_code,
                    )
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        with transaction.atomic():
            devices = self._get_target_devices_for_user(instance.user)

            for device in devices:
                self.set_device(device)
                response = self.destroy_objects(
                    "cards",
                    {"cards": {"id": instance.id}},
                )
                if response.status_code != status.HTTP_204_NO_CONTENT:
                    return Response(
                        {
                            "error": (
                                f"Erro ao deletar cartao da catraca {device.name}"
                            ),
                            "details": response.data,
                        },
                        status=response.status_code,
                    )

            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
