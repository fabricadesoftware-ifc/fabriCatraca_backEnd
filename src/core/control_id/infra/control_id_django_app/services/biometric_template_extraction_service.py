from __future__ import annotations

from src.core.control_id.infra.control_id_django_app.gateways import ControlIDGateway
from src.core.control_id.infra.control_id_django_app.models import (
    BiometricCaptureSession,
    Device,
)


class BiometricTemplateExtractionService:
    def __init__(self, gateway: ControlIDGateway | None = None) -> None:
        self.gateway = gateway or ControlIDGateway()

    def get_default_extractor_device(self) -> Device | None:
        return (
            Device.objects.filter(is_active=True, is_default=True).first()
            or Device.objects.filter(is_active=True).order_by("id").first()
        )

    @staticmethod
    def expand_packed_fingerprint_image(packed_image: bytes) -> bytes:
        if not packed_image:
            raise ValueError("Imagem biometrica vazia.")

        raw_image = bytearray(len(packed_image) * 2)
        write_index = 0
        for packed_byte in packed_image:
            raw_image[write_index] = ((packed_byte >> 4) & 0x0F) * 17
            raw_image[write_index + 1] = (packed_byte & 0x0F) * 17
            write_index += 2
        return bytes(raw_image)

    def extract_template_from_raw_capture(
        self,
        session: BiometricCaptureSession,
        packed_image: bytes,
    ) -> dict[str, str | int]:
        extractor_device = (
            session.extractor_device or self.get_default_extractor_device()
        )
        if extractor_device is None:
            raise ValueError(
                "Nenhuma catraca ativa disponivel para extrair o template."
            )

        raw_image = self.expand_packed_fingerprint_image(packed_image)
        payload = self.gateway.extract_template(extractor_device, raw_image)

        template_value = str(payload.get("template") or "").strip()
        if not template_value:
            raise ValueError(
                "A catraca nao retornou um template valido para a captura."
            )

        return {
            "quality": int(payload.get("quality", 0) or 0),
            "template": template_value,
        }
