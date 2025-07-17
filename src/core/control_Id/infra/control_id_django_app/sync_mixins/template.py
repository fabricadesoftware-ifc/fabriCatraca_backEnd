from rest_framework import status
from rest_framework.response import Response
from src.core.seedwork.infra.sync_mixins import CatracaSyncMixin

class TemplateSyncMixin(CatracaSyncMixin):
    def sync(self, request):
        try:
            # Carregar da catraca
            response = self.session.get(
                f"{self.base_url}/load_objects.fcgi",
                params={
                    "table": "templates",
                    "fields": ["id", "user_id", "template", "finger_type", "finger_position"],
                    "order_by": ["id"]
                }
            )
            
            if response.status_code != status.HTTP_200_OK:
                return Response({"error": response.text}, status=response.status_code)

            catraca_objects = response.json().get("templates", [])

            # Apagar todos do banco local
            self.model.objects.all().delete()

            # Cadastrar da catraca no banco local
            for data in catraca_objects:
                self.model.objects.create(
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