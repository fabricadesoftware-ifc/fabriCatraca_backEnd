from src.core.__seedwork__.infra.sync_mixins import CatracaSyncMixin

class CardSyncMixin(CatracaSyncMixin):
    def load_objects(self, object_type, fields=None, order_by=None):
        """Carrega cartões da catraca"""
        return super().load_objects(
            "cards",
            fields=["id", "value", "user_id"],
            order_by=["id"]
        )

    def create_objects(self, object_type, objects):
        """Cria cartões na catraca"""
        return super().create_objects("cards", objects)

    def update_objects(self, object_type, objects, where):
        """Atualiza cartões na catraca"""
        return super().update_objects("cards", objects, where)

    def destroy_objects(self, object_type, where):
        """Deleta cartões na catraca"""
        return super().destroy_objects("cards", where) 