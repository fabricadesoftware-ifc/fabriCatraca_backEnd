from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status


class UserAccessRuleSyncMixin(ControlIDSyncMixin):
    def create_in_catraca(self, instance):
        response = self.create_objects("user_access_rules", [{
            "user_id": instance.user.id,
            "access_rule_id": instance.access_rule.id
        }])
        return response

    def update_in_catraca(self, instance):
        response = self.update_objects(
            "user_access_rules",
            {
                "user_id": instance.user.id,
                "access_rule_id": instance.access_rule.id
            },
            {"user_access_rules": {
                "user_id": instance.user.id,
                "access_rule_id": instance.access_rule.id
            }}
        )
        return response

    def delete_in_catraca(self, instance):
        response = self.destroy_objects(
            "user_access_rules",
            {"user_access_rules": {
                "user_id": instance.user.id,
                "access_rule_id": instance.access_rule.id
            }}
        )
        return response

    def sync_from_catraca(self):
        try:
            from src.core.control_Id.infra.control_id_django_app.models import UserAccessRule, AccessRule
            from src.core.user.infra.user_django_app.models import User
            
            catraca_objects = self.load_objects("user_access_rules")

            with transaction.atomic():
                UserAccessRule.objects.all().delete()
                for data in catraca_objects:
                    user = User.objects.get(id=data["user_id"])
                    access_rule = AccessRule.objects.get(id=data["access_rule_id"])
                    UserAccessRule.objects.create(
                        user=user,
                        access_rule=access_rule
                    )

            return Response({
                "success": True,
                "message": f"Sincronizadas {len(catraca_objects)} associações usuário-regra"
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

