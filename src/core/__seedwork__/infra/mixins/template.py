from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

class TemplateSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("templates", [{
            "id": instance.id,
            "user_id": instance.user.id,
            "template": instance.template,
            "finger_type": 0,  # dedo comum
            "finger_position": 0  # campo reservado
        }])
        return response

    def update_in_catraca(self, instance):
        response = self.update_objects(
            "templates",
            {
                "id": instance.id,
                "user_id": instance.user.id,
                "template": instance.template,
                "finger_type": 0,  # dedo comum
                "finger_position": 0  # campo reservado
            },
            {"templates": {"id": instance.id}}
        )
        return response

    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "templates",
            {"templates": {"id": instance.id}}
        )
        return response

    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import Template
            from src.core.user.infra.user_django_app.models import User
            
            catraca_objects = self.load_objects(
                "templates",
                fields=["id", "user_id", "template", "finger_type", "finger_position"]
            )

            with transaction.atomic():
                Template.objects.all().delete()
                for data in catraca_objects:
                    Template.objects.create(
                        id=data["id"],
                        user_id=data["user_id"],
                        template=data["template"]
                    )

            return Response({
                "success": True,
                "message": f"Sincronizados {len(catraca_objects)} templates"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
