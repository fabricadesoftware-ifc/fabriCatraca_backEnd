from src.core.__seedwork__.infra import ControlIDSyncMixin

class AccessRuleSyncMixin(ControlIDSyncMixin):
    def load_objects(self, object_type, fields=None, order_by=None):
        """Carrega regras de acesso da catraca"""
        return super().load_objects(
            "access_rules",
            fields=["id", "name", "type", "priority"],
            order_by=["id"]
        )

    def create_objects(self, object_type, objects):
        """Cria regras de acesso na catraca"""
        return super().create_objects("access_rules", objects)

    def update_objects(self, object_type, objects, where):
        """Atualiza regras de acesso na catraca"""
        return super().update_objects("access_rules", objects, where)

    def destroy_objects(self, object_type, where):
        """Deleta regras de acesso na catraca"""
        return super().destroy_objects("access_rules", where) 