"""
Script para testar criação dos novos models CatraConfig e PushServerConfig
"""
import os
import sys

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
django.setup()

def test_new_models():
    """Testa se os novos models foram criados corretamente"""
    print("\n" + "="*80)
    print("TESTE DE NOVOS MODELS - CatraConfig e PushServerConfig")
    print("="*80)
    
    # Importa os models
    try:
        from src.core.control_id_config.infra.control_id_config_django_app.models import (
            CatraConfig, PushServerConfig
        )
        print("✅ Models importados com sucesso!")
    except ImportError as e:
        print(f"❌ Erro ao importar models: {e}")
        return
    
    # Importa os serializers
    try:
        from src.core.control_id_config.infra.control_id_config_django_app.serializers import (
            CatraConfigSerializer, PushServerConfigSerializer
        )
        print("✅ Serializers importados com sucesso!")
    except ImportError as e:
        print(f"❌ Erro ao importar serializers: {e}")
        return
    
    # Importa as views
    try:
        from src.core.control_id_config.infra.control_id_config_django_app.views.catra_config import (
            CatraConfigViewSet
        )
        from src.core.control_id_config.infra.control_id_config_django_app.views.push_server_config import (
            PushServerConfigViewSet
        )
        print("✅ ViewSets importados com sucesso!")
    except ImportError as e:
        print(f"❌ Erro ao importar views: {e}")
        return
    
    # Importa os mixins
    try:
        from src.core.control_id_config.infra.control_id_config_django_app.mixins.catra_config_mixin import (
            CatraConfigSyncMixin
        )
        from src.core.control_id_config.infra.control_id_config_django_app.mixins.push_server_config_mixin import (
            PushServerConfigSyncMixin
        )
        print("✅ Mixins importados com sucesso!")
    except ImportError as e:
        print(f"❌ Erro ao importar mixins: {e}")
        return
    
    print("\n" + "-"*80)
    print("ESTRUTURA DOS MODELS")
    print("-"*80)
    
    # Testa CatraConfig
    print("\n📦 CatraConfig:")
    print(f"   Fields: {[f.name for f in CatraConfig._meta.get_fields()]}")
    print(f"   Gateway choices: {CatraConfig.GATEWAY_CHOICES}")
    print(f"   Operation mode choices: {CatraConfig.OPERATION_MODE_CHOICES}")
    
    # Testa PushServerConfig
    print("\n📦 PushServerConfig:")
    print(f"   Fields: {[f.name for f in PushServerConfig._meta.get_fields()]}")
    
    print("\n" + "-"*80)
    print("MÉTODOS DOS MIXINS")
    print("-"*80)
    
    # Verifica métodos do CatraConfigSyncMixin
    print("\n🔧 CatraConfigSyncMixin:")
    mixin_methods = [m for m in dir(CatraConfigSyncMixin) if not m.startswith('_')]
    print(f"   Métodos: {', '.join(mixin_methods)}")
    
    # Verifica métodos do PushServerConfigSyncMixin
    print("\n🔧 PushServerConfigSyncMixin:")
    mixin_methods = [m for m in dir(PushServerConfigSyncMixin) if not m.startswith('_')]
    print(f"   Métodos: {', '.join(mixin_methods)}")
    
    print("\n" + "="*80)
    print("✅ TODOS OS COMPONENTES FORAM CRIADOS COM SUCESSO!")
    print("="*80)
    
    print("\n📝 Próximos passos:")
    print("   1. Executar migrations: python src/manage.py makemigrations")
    print("   2. Aplicar migrations: python src/manage.py migrate")
    print("   3. Testar sincronização com catraca real")
    print("\n💡 Endpoints disponíveis:")
    print("   - GET/POST /api/config/catra-configs/")
    print("   - POST /api/config/catra-configs/sync-from-catraca/")
    print("   - GET/POST /api/config/push-server-configs/")
    print("   - POST /api/config/push-server-configs/sync-from-catraca/")

if __name__ == "__main__":
    test_new_models()
