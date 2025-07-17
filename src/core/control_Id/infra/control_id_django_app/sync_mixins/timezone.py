from src.core.seedwork.infra.sync_mixins import CatracaSyncMixin

class TimeZoneSyncMixin(CatracaSyncMixin):
    def load_objects(self, object_type, fields=None, order_by=None):
        """Carrega zonas de tempo da catraca"""
        return super().load_objects(
            "time_zones",
            fields=["id", "name"],
            order_by=["id"]
        )

    def create_objects(self, object_type, objects):
        """Cria zonas de tempo na catraca"""
        return super().create_objects("time_zones", objects)

    def update_objects(self, object_type, objects, where):
        """Atualiza zonas de tempo na catraca"""
        return super().update_objects("time_zones", objects, where)

    def destroy_objects(self, object_type, where):
        """Deleta zonas de tempo na catraca"""
        return super().destroy_objects("time_zones", where) 