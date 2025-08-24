from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import GroupAccessRule, CustomGroup, AccessRule


class GroupBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomGroup
        fields = ['id', 'name']


class AccessRuleBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRule
        fields = ['id', 'name']


class GroupAccessRuleSerializer(serializers.ModelSerializer):
    # ✅ Saída: mostra os dados completos
    group = GroupBasicSerializer(read_only=True)
    access_rule = AccessRuleBasicSerializer(read_only=True)

    # ✅ Entrada: permite enviar apenas os ids
    group_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=CustomGroup.objects.all(),
        source="group",
        required=True
    )
    access_rule_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=AccessRule.objects.all(),
        source="access_rule",
        required=True
    )

    class Meta:
        model = GroupAccessRule
        fields = ['id', 'group', 'group_id', 'access_rule', 'access_rule_id']
        read_only_fields = ['id']
        