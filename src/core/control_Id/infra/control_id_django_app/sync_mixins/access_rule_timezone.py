from src.core.__seedwork__.infra import ControlIDSyncMixin

class AccessRuleTimeZoneSyncMixin(ControlIDSyncMixin):
    def load_objects(self, object_type, fields=None, order_by=None):
        """Carrega associações regra-zona da catraca"""
        return super().load_objects(
            "access_rule_time_zones",
            fields=["access_rule_id", "time_zone_id"],
            order_by=["access_rule_id", "time_zone_id"]
        )

    def create_objects(self, object_type, objects):
        """Cria associações regra-zona na catraca"""
        return super().create_objects("access_rule_time_zones", objects)

    def update_objects(self, object_type, objects, where):
        """Atualiza associações regra-zona na catraca"""
        return super().update_objects("access_rule_time_zones", objects, where)

    def destroy_objects(self, object_type, where):
        """Deleta associações regra-zona na catraca"""
        return super().destroy_objects("access_rule_time_zones", where) 