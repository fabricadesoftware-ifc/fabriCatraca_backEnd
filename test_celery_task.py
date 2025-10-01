"""
Script para testar a task Celery de sincronização diretamente
"""

import os
import sys
import django

# Configura Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from src.core.control_id_config.infra.control_id_config_django_app.tasks import run_config_sync

print("=" * 80)
print("🔄 EXECUTANDO CELERY TASK: run_config_sync")
print("=" * 80)
print()

# Executa a task diretamente (sem Celery)
result = run_config_sync()

print()
print("=" * 80)
print("📊 RESULTADO:")
print("=" * 80)
import json
print(json.dumps(result, indent=2))
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
