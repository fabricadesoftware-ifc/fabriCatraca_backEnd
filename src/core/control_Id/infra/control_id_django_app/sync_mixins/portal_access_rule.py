from src.core.__seedwork__.infra import ControlIDSyncMixin

class PortalAccessRuleSyncMixin(ControlIDSyncMixin):
    def load_objects(self, object_type, fields=None, order_by=None):
        """Carrega associações portal-regra da catraca"""
        return super().load_objects(
            "portal_access_rules",
            fields=["portal_id", "access_rule_id"],
            order_by=["portal_id", "access_rule_id"]
        )

    def create_objects(self, object_type, objects):
        """Cria associações portal-regra na catraca"""
        return super().create_objects("portal_access_rules", objects)

    def update_objects(self, object_type, objects, where):
        """Atualiza associações portal-regra na catraca"""
        return super().update_objects("portal_access_rules", objects, where)

    def destroy_objects(self, object_type, where):
        """Deleta associações portal-regra na catraca"""
        return super().destroy_objects("portal_access_rules", where) 