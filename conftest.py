from __future__ import annotations

from itertools import count
from unittest.mock import Mock

import factory
import pytest
from faker import Faker
from rest_framework.test import APIClient

from src.core.user.infra.user_django_app.models import User
from src.core.control_id.infra.control_id_django_app.models import Device
from src.core.control_id_config.infra.control_id_config_django_app.models import (
    CatraConfig,
    HardwareConfig,
    PushServerConfig,
    SecurityConfig,
    SystemConfig,
    UIConfig,
)
from src.core.control_id_monitor.infra.control_id_monitor_django_app.models import (
    MonitorConfig,
)

fake = Faker("pt_BR")
test_password = "Teste-Forte-123"
_ip_sequence = count(10)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    name = factory.Faker("name", locale="pt_BR")
    email = factory.Sequence(lambda n: f"user{n}@example.test")
    registration = factory.Sequence(lambda n: f"REG{n:06d}")
    app_role = User.AppRole.ALUNO
    is_active = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or test_password)
        if create:
            self.save(update_fields=["password"])


class AdminUserFactory(UserFactory):
    app_role = User.AppRole.ADMIN
    is_staff = True
    is_superuser = True


class OperatorUserFactory(UserFactory):
    app_role = User.AppRole.GUARITA
    is_staff = False
    is_superuser = False


class DeviceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Device

    name = factory.Sequence(lambda n: f"Catraca {n:02d}")
    ip = factory.LazyFunction(lambda: f"192.0.2.{next(_ip_sequence)}")
    username = "admin"
    password = "admin"
    is_active = True
    is_default = False


class SystemConfigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SystemConfig

    device = factory.SubFactory(DeviceFactory)
    auto_reboot_hour = 3
    auto_reboot_minute = 0
    clear_expired_users = False
    keep_user_image = True
    url_reboot_enabled = True
    web_server_enabled = True
    online = True
    local_identification = True
    language = "pt_BR"
    catra_timeout = 30000


class HardwareConfigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HardwareConfig

    device = factory.SubFactory(DeviceFactory)
    beep_enabled = True
    bell_enabled = False
    bell_relay = 2
    ssh_enabled = False
    relayN_enabled = False
    relayN_timeout = 5
    relayN_auto_close = True
    door_sensorN_enabled = False
    door_sensorN_idle = 10
    doorN_interlock = False
    network_interlock_enabled = False
    network_interlock_api_bypass_enabled = False
    network_interlock_rex_bypass_enabled = False
    exception_mode = "none"
    doorN_exception_mode = False


class SecurityConfigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SecurityConfig

    device = factory.SubFactory(DeviceFactory)
    password_only = False
    hide_password_only = False
    password_only_tip = ""
    hide_name_on_identification = False
    denied_transaction_code = ""
    send_code_when_not_identified = False
    send_code_when_not_authorized = False
    verbose_logging_enabled = True
    log_type = False
    multi_factor_authentication_enabled = False


class UIConfigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UIConfig

    device = factory.SubFactory(DeviceFactory)
    screen_always_on = True


class CatraConfigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CatraConfig

    device = factory.SubFactory(DeviceFactory)
    anti_passback = False
    daily_reset = False
    gateway = "clockwise"
    operation_mode = "blocked"


class PushServerConfigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PushServerConfig

    device = factory.SubFactory(DeviceFactory)
    push_request_timeout = 15000
    push_request_period = 60
    push_remote_address = factory.Sequence(lambda n: f"192.0.2.{100 + n}:8080")


class MonitorConfigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MonitorConfig

    device = factory.SubFactory(DeviceFactory)
    request_timeout = 1000
    hostname = ""
    port = ""
    path = "api/notifications"


def _authenticated_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def test_user_password():
    return test_password


@pytest.fixture
def user_factory(db):
    return UserFactory


@pytest.fixture
def admin_user(db):
    return AdminUserFactory()


@pytest.fixture
def operator_user(db):
    return OperatorUserFactory()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def anonymous_client():
    return APIClient()


@pytest.fixture
def api_client(admin_user):
    return _authenticated_client(admin_user)


@pytest.fixture
def api_client_admin(admin_user):
    return _authenticated_client(admin_user)


@pytest.fixture
def api_client_operator(operator_user):
    return _authenticated_client(operator_user)


@pytest.fixture
def admin_api_client(api_client_admin):
    return api_client_admin


@pytest.fixture
def operator_api_client(api_client_operator):
    return api_client_operator


@pytest.fixture
def device_factory(db):
    return DeviceFactory


@pytest.fixture
def control_id(device_factory):
    return device_factory()


@pytest.fixture
def catraca_device(device_factory):
    return device_factory(name="Catraca Principal", ip="192.0.2.20")


@pytest.fixture
def system_config_factory(db):
    return SystemConfigFactory


@pytest.fixture
def hardware_config_factory(db):
    return HardwareConfigFactory


@pytest.fixture
def security_config_factory(db):
    return SecurityConfigFactory


@pytest.fixture
def ui_config_factory(db):
    return UIConfigFactory


@pytest.fixture
def catra_config_factory(db):
    return CatraConfigFactory


@pytest.fixture
def catraca_config(catra_config_factory):
    return catra_config_factory()


@pytest.fixture
def push_server_config_factory(db):
    return PushServerConfigFactory


@pytest.fixture
def monitor_config_factory(db):
    return MonitorConfigFactory


@pytest.fixture
def make_response():
    def build(status_code=200, json_data=None, text=None):
        response = Mock()
        response.status_code = status_code
        payload = {} if json_data is None else json_data
        response.json.return_value = payload
        response.text = (
            text if text is not None else ("" if payload == {} else str(payload))
        )
        response.content = response.text.encode()
        response.raise_for_status = Mock()
        return response

    return build


@pytest.fixture
def mock_catraca_response():
    def create_response(config_type="system", success=True, **extra_data):
        if not success:
            return {"error": "Connection failed", "code": 500}

        responses = {
            "system": {
                "general": {
                    "online": "1",
                    "local_identification": "1",
                    "language": "pt",
                    "catra_timeout": "30000",
                }
            },
            "catra": {
                "catra": {
                    "anti_passback": "0",
                    "daily_reset": "0",
                    "gateway": "clockwise",
                    "operation_mode": "blocked",
                }
            },
            "push_server": {
                "push_server": {
                    "push_request_timeout": "15000",
                    "push_request_period": "60",
                    "push_remote_address": "192.0.2.50:8080",
                }
            },
            "hardware": {
                "general": {
                    "beep_enabled": "1",
                    "bell_enabled": "0",
                    "bell_relay": "2",
                    "exception_mode": "none",
                },
                "alarm": {},
            },
            "security": {
                "identifier": {
                    "verbose_logging": "1",
                    "log_type": "0",
                    "multi_factor_authentication": "1",
                }
            },
            "ui": {},
        }

        response = responses.get(config_type, {}).copy()
        for key, value in extra_data.items():
            if isinstance(value, dict) and isinstance(response.get(key), dict):
                response[key] = {**response[key], **value}
            else:
                response[key] = value
        return response

    return create_response
