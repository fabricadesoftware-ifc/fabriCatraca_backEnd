from src.core.__seedwork__.infra import ControlIDSyncMixin
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action

class UserSyncMixin(ControlIDSyncMixin):
    def load_objects(self, object_type, fields=None, order_by=None):
        """Carrega usuários da catraca"""
        return super().load_objects(
            "users",
            fields=["id", "name", "registration", "user_type_id"],
            order_by=["id"]
        )

    def create_objects(self, object_type, objects):
        """Cria usuários na catraca"""
        return super().create_objects("users", objects)

    def update_objects(self, object_type, objects, where):
        """Atualiza usuários na catraca"""
        return super().update_objects("users", objects, where)

    def destroy_objects(self, object_type, where):
        """Deleta usuários na catraca"""
        return super().destroy_objects("users", where) 