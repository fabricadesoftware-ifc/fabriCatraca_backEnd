from src.core.__seedwork__.infra.sync_mixins import CatracaSyncMixin

class TimeSpanSyncMixin(CatracaSyncMixin):
    def load_objects(self, object_type, fields=None, order_by=None):
        """Carrega intervalos de tempo da catraca"""
        return super().load_objects(
            "time_spans",
            fields=["id", "time_zone_id", "start", "end", "sun", "mon", "tue", "wed", "thu", "fri", "sat", "hol1", "hol2", "hol3"],
            order_by=["id"]
        )

    def create_objects(self, object_type, objects):
        """Cria intervalos de tempo na catraca"""
        return super().create_objects("time_spans", objects)

    def update_objects(self, object_type, objects, where):
        """Atualiza intervalos de tempo na catraca"""
        return super().update_objects("time_spans", objects, where)

    def destroy_objects(self, object_type, where):
        """Deleta intervalos de tempo na catraca"""
        return super().destroy_objects("time_spans", where) 