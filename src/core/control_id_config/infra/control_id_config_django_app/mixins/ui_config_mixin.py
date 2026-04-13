from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework.response import Response
from rest_framework import status


class UIConfigSyncMixin(ControlIDSyncMixin):
    """Mixin para sincronizacao de configuracoes de interface."""

    def update_ui_config_in_catraca(self, instance):
        """Nenhuma configuracao de UI e enviada ao firmware atual."""
        return Response(
            {
                "success": True,
                "message": "Nenhuma configuracao de interface esta disponivel para o firmware atual.",
            },
            status=status.HTTP_200_OK,
        )

    def sync_ui_config_from_catraca(self):
        """Mantem o registro de UI apenas para compatibilidade local."""
        try:
            from ..models import UIConfig

            config, created = UIConfig.objects.get_or_create(
                device=self.device,
                defaults={},
            )

            return Response(
                {
                    "success": True,
                    "message": (
                        f"Configuracao de interface {'criada' if created else 'mantida'} localmente."
                    ),
                    "config_id": config.id,
                }
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
