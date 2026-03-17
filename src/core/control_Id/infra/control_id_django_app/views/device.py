import requests
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from src.core.control_Id.infra.control_id_django_app.device_registry_sync import (
    DeviceRegistrySyncService,
)
from src.core.control_Id.infra.control_id_django_app.models.device import Device
from src.core.control_Id.infra.control_id_django_app.serializers.device import DeviceSerializer
from drf_spectacular.utils import extend_schema

@extend_schema(tags=["Devices"])
class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    filterset_fields = ['name', 'ip', 'is_active', 'is_default']
    search_fields = ['name', 'ip']
    ordering_fields = ['name', 'ip', 'is_active', 'is_default']

    def _build_sync_mixin(self, device: Device):
        from src.core.__seedwork__.infra import ControlIDSyncMixin

        mixin = ControlIDSyncMixin()
        mixin.set_device(device)
        return mixin

    def _inspect_remote_registry(self, device: Device):
        sync_service = DeviceRegistrySyncService()
        expected = sync_service._desired_values()
        expected_by_id = {int(item["id"]): item for item in expected}

        mixin = self._build_sync_mixin(device)
        remote_registry = mixin.load_objects("devices", fields=["id", "name", "ip"], order_by=["id"])
        remote_by_id = {int(item["id"]): item for item in remote_registry if item.get("id") is not None}

        rows = []
        all_ids = sorted(set(expected_by_id) | set(remote_by_id))
        for device_id in all_ids:
            expected_item = expected_by_id.get(device_id)
            remote_item = remote_by_id.get(device_id)
            if expected_item and remote_item:
                status_label = "ok" if (
                    str(expected_item.get("name")) == str(remote_item.get("name"))
                    and str(expected_item.get("ip")) == str(remote_item.get("ip"))
                ) else "divergente"
            elif expected_item:
                status_label = "faltando"
            else:
                status_label = "extra"

            rows.append(
                {
                    "id": device_id,
                    "status": status_label,
                    "expected": expected_item,
                    "remote": remote_item,
                }
            )

        return {
            "device_id": device.id,
            "device_name": device.name,
            "rows": rows,
            "expected_count": len(expected),
            "remote_count": len(remote_registry),
        }

    def _get_active_logo_slot(self, device: Device):
        mixin = self._build_sync_mixin(device)
        response = mixin._make_request(
            "get_configuration.fcgi",
            json_data={"general": ["show_logo"]},
        )
        if response.status_code != 200:
            return 0
        general = response.json().get("general", {})
        try:
            return int(str(general.get("show_logo", 0)) or 0)
        except (TypeError, ValueError):
            return 0

    def _parse_logo_slot(self, slot_id):
        slot_id_int = int(slot_id)
        if slot_id_int < 1 or slot_id_int > 8:
            raise ValueError("slot_id deve estar entre 1 e 8")
        return slot_id_int

    def _fetch_logo_response(self, device: Device, slot_id: int):
        mixin = self._build_sync_mixin(device)
        session = mixin.login()
        return requests.post(
            mixin.get_url(f"logo.fcgi?session={session}&id={slot_id}"),
            timeout=30,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Se está criando como default, remove o default de outros
        if serializer.validated_data.get('is_default'):
            Device.objects.filter(is_default=True).update(is_default=False)
            
        instance = serializer.save()
        DeviceRegistrySyncService().sync_all_active_devices()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data.get('is_default'):
            Device.objects.filter(is_default=True).exclude(id=instance.id).update(is_default=False)

        instance = serializer.save()
        DeviceRegistrySyncService().sync_all_active_devices()
        return Response(self.get_serializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        DeviceRegistrySyncService().sync_all_active_devices()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def test_connection(self, request, pk=None):
        """Testa a conexão com o dispositivo"""
        device = self.get_object()
        
        try:
            # Tenta fazer login
            from src.core.__seedwork__.infra import ControlIDSyncMixin
            mixin = ControlIDSyncMixin()
            mixin.set_device(device)
            mixin.login()
            
            
            Device.objects.filter(id=device.id).update(is_active=True)
            return Response({
                "success": True,
                "message": "Conexão estabelecida com sucesso"
            })
        except Exception as e:
            Device.objects.filter(id=device.id).update(is_active=False)
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def sync_registry(self, request):
        """Sincroniza a tabela devices em todas as catracas ativas."""
        result = DeviceRegistrySyncService().sync_all_active_devices()
        return Response(result, status=status.HTTP_200_OK if result.get("success") else status.HTTP_207_MULTI_STATUS)

    @action(detail=True, methods=['get'])
    def registry(self, request, pk=None):
        device = self.get_object()
        try:
            report = self._inspect_remote_registry(device)
            return Response(report)
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='sync-registry')
    def sync_remote_registry(self, request, pk=None):
        device = self.get_object()
        result = DeviceRegistrySyncService().sync_all_active_devices(target_devices=[device])
        status_code = status.HTTP_200_OK if result.get("success") else status.HTTP_207_MULTI_STATUS
        return Response(result, status=status_code)

    @action(detail=True, methods=['get'], url_path='logos')
    def logos(self, request, pk=None):
        device = self.get_object()
        active_slot = self._get_active_logo_slot(device)
        slots = []
        for slot_id in range(1, 9):
            try:
                logo_response = self._fetch_logo_response(device, slot_id)
                content_type = (logo_response.headers.get("Content-Type") or "").lower()
                has_logo = (
                    logo_response.status_code == 200
                    and "image/png" in content_type
                    and bool(logo_response.content)
                )
                slots.append(
                    {
                        "slot_id": slot_id,
                        "has_logo": has_logo,
                        "is_active": active_slot == slot_id,
                        "content_type": content_type,
                    }
                )
            except Exception:
                slots.append(
                    {
                        "slot_id": slot_id,
                        "has_logo": False,
                        "is_active": active_slot == slot_id,
                        "content_type": None,
                    }
                )

        return Response(
            {
                "device_id": device.id,
                "device_name": device.name,
                "active_slot": active_slot,
                "slots": slots,
            }
        )

    @action(detail=True, methods=['get'], url_path=r'logos/(?P<slot_id>\d+)/image')
    def logo_image(self, request, pk=None, slot_id=None):
        device = self.get_object()
        try:
            slot_id_int = self._parse_logo_slot(slot_id)
        except ValueError as exc:
            return Response({"success": False, "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        response = self._fetch_logo_response(device, slot_id_int)
        content_type = (response.headers.get("Content-Type") or "").lower()
        if response.status_code == 200 and "image/png" in content_type and response.content:
            return HttpResponse(response.content, content_type="image/png")
        return Response(
            {"success": False, "error": f"Nenhum logo encontrado no slot {slot_id_int}"},
            status=status.HTTP_404_NOT_FOUND,
        )

    @action(
        detail=True,
        methods=['post'],
        url_path=r'logos/(?P<slot_id>\d+)/upload',
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_logo(self, request, pk=None, slot_id=None):
        device = self.get_object()
        try:
            slot_id_int = self._parse_logo_slot(slot_id)
        except ValueError as exc:
            return Response({"success": False, "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"success": False, "error": "Arquivo PNG é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)
        if file_obj.size > 1024 * 1024:
            return Response({"success": False, "error": "Logo não pode ultrapassar 1MB"}, status=status.HTTP_400_BAD_REQUEST)

        mixin = self._build_sync_mixin(device)
        session = mixin.login()
        response = requests.post(
            mixin.get_url(f"logo_change.fcgi?session={session}&id={slot_id_int}"),
            data=file_obj.read(),
            headers={"Content-Type": "application/octet-stream"},
            timeout=60,
        )
        if response.status_code != 200:
            return Response(
                {"success": False, "error": "Erro ao enviar logo", "details": response.text},
                status=response.status_code,
            )
        return Response({"success": True, "slot_id": slot_id_int})

    @action(detail=True, methods=['post'], url_path=r'logos/(?P<slot_id>\d+)/delete')
    def delete_logo(self, request, pk=None, slot_id=None):
        device = self.get_object()
        try:
            slot_id_int = self._parse_logo_slot(slot_id)
        except ValueError as exc:
            return Response({"success": False, "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        mixin = self._build_sync_mixin(device)
        session = mixin.login()
        response = requests.post(
            mixin.get_url(f"logo_destroy.fcgi?session={session}&id={slot_id_int}"),
            timeout=30,
        )
        if response.status_code != 200:
            return Response(
                {"success": False, "error": "Erro ao remover logo", "details": response.text},
                status=response.status_code,
            )

        active_slot = self._get_active_logo_slot(device)
        if active_slot == slot_id_int:
            mixin._make_request("set_configuration.fcgi", json_data={"general": {"show_logo": "0"}})

        return Response({"success": True, "slot_id": slot_id_int})

    @action(detail=True, methods=['post'], url_path='logos/show')
    def show_logo(self, request, pk=None):
        device = self.get_object()
        slot_id = int(request.data.get("slot_id", 0) or 0)
        if slot_id < 0 or slot_id > 8:
            return Response({"success": False, "error": "slot_id deve estar entre 0 e 8"}, status=status.HTTP_400_BAD_REQUEST)

        mixin = self._build_sync_mixin(device)
        response = mixin._make_request(
            "set_configuration.fcgi",
            json_data={"general": {"show_logo": str(slot_id)}},
        )
        if response.status_code != 200:
            return Response(
                {"success": False, "error": "Erro ao selecionar logo", "details": response.text},
                status=response.status_code,
            )
        return Response({"success": True, "active_slot": slot_id})
