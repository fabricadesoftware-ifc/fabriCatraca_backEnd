"""
Script para testar a sincronização de configurações manualmente
Executa a task de sync diretamente sem precisar do Celery
"""

import os
import sys
import django

# Configura Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from src.core.control_id_config.infra.control_id_config_django_app.sync_config import sync_all_configs

print("=" * 80)
print("🔄 EXECUTANDO SYNC DE CONFIGURAÇÕES (MODO DEBUG)")
print("=" * 80)
print()

result = sync_all_configs()

print()
print("=" * 80)
print("📊 RESULTADO FINAL:")
print("=" * 80)
print(result)
print()

# Verificar o que foi salvo no banco
from src.core.control_id_config.infra.control_id_config_django_app.models import SystemConfig

print("=" * 80)
print("🔍 VERIFICANDO BANCO DE DADOS:")
print("=" * 80)

configs = SystemConfig.objects.all()
for config in configs:
    print(f"\nSystemConfig ID: {config.id}")
    print(f"  Device: {config.device.name if config.device else 'N/A'}")
    print(f"  online: {config.online} (type: {type(config.online).__name__})")
    print(f"  clear_expired_users: {config.clear_expired_users} (type: {type(config.clear_expired_users).__name__})")
    print(f"  url_reboot_enabled: {config.url_reboot_enabled} (type: {type(config.url_reboot_enabled).__name__})")

print()
print("=" * 80)
