from .system_config import SystemConfigSerializer
from .hardware_config import HardwareConfigSerializer
from .security_config import SecurityConfigSerializer
from .ui_config import UIConfigSerializer
from .catra_config import CatraConfigSerializer
from .push_server_config import PushServerConfigSerializer

# Serializer simples para o bloco monitor (payload dinâmico)
from rest_framework import serializers


# Mantemos referência ao serializer forte baseado em model

__all__ = [
    'SystemConfigSerializer',
    'HardwareConfigSerializer', 
    'SecurityConfigSerializer',
    'UIConfigSerializer',
    'CatraConfigSerializer',
    'PushServerConfigSerializer'
]