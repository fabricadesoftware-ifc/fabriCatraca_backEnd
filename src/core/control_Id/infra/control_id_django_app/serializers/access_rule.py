from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import (
    AccessRule,
    PortalAccessRule,
    AccessRuleTimeZone,
)

class AccessRuleSerializer(serializers.ModelSerializer):
    areas = serializers.SerializerMethodField()
    time_zones = serializers.SerializerMethodField()
    class Meta:
        model = AccessRule
        fields = ['id', 'name', 'type', 'priority', 'areas', 'time_zones']
        read_only_fields = ['id']

    def get_time_zones(self, obj):
        links = (
            AccessRuleTimeZone.objects
            .filter(access_rule=obj)
            .select_related('time_zone')
        )
        return [
            {
                'id': link.time_zone.id,
                'name': link.time_zone.name,
            }
            for link in links
        ]

    def get_areas(self, obj):
        links = (
            PortalAccessRule.objects
            .filter(access_rule=obj)
            .select_related('portal__area_from', 'portal__area_to')
        )
        areas_by_id = {}
        for link in links:
            portal = link.portal
            if portal.area_from and portal.area_from.id not in areas_by_id:
                areas_by_id[portal.area_from.id] = {
                    'id': portal.area_from.id,
                    'name': portal.area_from.name,
                }
            if portal.area_to and portal.area_to.id not in areas_by_id:
                areas_by_id[portal.area_to.id] = {
                    'id': portal.area_to.id,
                    'name': portal.area_to.name,
                }
        return list(areas_by_id.values())