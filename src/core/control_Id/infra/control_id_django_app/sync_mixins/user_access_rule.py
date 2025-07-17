from src.core.__seedwork__.infra.sync_mixins import CatracaSyncMixin

class UserAccessRuleSyncMixin(CatracaSyncMixin):
    def load_objects(self, object_type, fields=None, order_by=None):
        """Carrega associações usuário-regra da catraca"""
        return super().load_objects(
            "user_access_rules",
            fields=["user_id", "access_rule_id"],
            order_by=["user_id", "access_rule_id"]
        )

    def create_objects(self, object_type, objects):
        """Cria associações usuário-regra na catraca"""
        return super().create_objects("user_access_rules", objects)

    def update_objects(self, object_type, objects, where):
        """Atualiza associações usuário-regra na catraca"""
        return super().update_objects("user_access_rules", objects, where)

    def destroy_objects(self, object_type, where):
        """Deleta associações usuário-regra na catraca"""
        return super().destroy_objects("user_access_rules", where) 