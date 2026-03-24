from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db import transaction
from drf_spectacular.utils import extend_schema

from src.core.control_Id.infra.control_id_django_app.models.template import Template
from src.core.control_Id.infra.control_id_django_app.serializers.template import (
    TemplateSerializer,
)
from src.core.__seedwork__.infra.mixins import TemplateSyncMixin
from src.core.control_Id.infra.control_id_django_app.models.device import Device
from src.core.control_Id.infra.control_id_django_app.services import (
    TemplateEnrollmentError,
    TemplateEnrollmentService,
)


@extend_schema(tags=["Templates"])
class TemplateViewSet(TemplateSyncMixin, viewsets.ModelViewSet):
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer
    filterset_fields = ["user"]

    def create(self, request, *args, **kwargs):
        """Cria template via serviço de aplicação (modo remote/local)."""
        try:
            enrollment_mode = (request.data.get("enrollment_mode") or "remote").lower()
            user_id = (
                request.data.get("user_id")
                or request.query_params.get("user_id")
                or request.data.get("user")
            )
            if not user_id:
                return Response(
                    {"error": "Usuário (user_id) é obrigatório"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            service = TemplateEnrollmentService()
            result = service.enroll(
                user_id=user_id,
                enrollment_mode=enrollment_mode,
                enrollment_device_id=request.data.get("enrollment_device_id"),
                captured_template=request.data.get("captured_template")
                or request.data.get("template"),
                finger_type=int(request.data.get("finger_type", 0) or 0),
                finger_position=int(request.data.get("finger_position", 0) or 0),
            )

            serializer = self.get_serializer(result.instance)
            response_data = dict(serializer.data)
            response_data["enrollment_mode"] = result.enrollment_mode
            response_data["replication_errors"] = result.replication_errors

            return Response(response_data, status=status.HTTP_201_CREATED)

        except TemplateEnrollmentError as exc:
            payload = {"error": exc.message}
            if exc.details is not None:
                payload["details"] = exc.details
            return Response(payload, status=exc.status_code)

        except Exception as e:
            import traceback

            traceback.print_exc()  # Log no console para debug
            return Response(
                {
                    "error": "Erro interno no servidor ao processar biometria",
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

            devices = Device.objects.filter(is_active=True)

            for device in devices:
                self.set_device(device)
                response = self.update_objects(
                    "templates",
                    [
                        {
                            "id": instance.id,
                            "user_id": instance.user.id,
                            "template": instance.template,
                        }
                    ],
                    {"templates": {"id": instance.id}},
                )
                if response.status_code != status.HTTP_200_OK:
                    return Response(
                        {
                            "error": f"Erro ao atualizar template na catraca {device.name}",
                            "details": response.data,
                        },
                        status=response.status_code,
                    )
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        with transaction.atomic():
            devices = Device.objects.filter(is_active=True)

            for device in devices:
                self.set_device(device)
                response = self.destroy_objects(
                    "templates", {"templates": {"id": instance.id}}
                )
                if response.status_code != status.HTTP_204_NO_CONTENT:
                    return Response(
                        {
                            "error": f"Erro ao deletar template da catraca {device.name}",
                            "details": response.data,
                        },
                        status=response.status_code,
                    )

            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
