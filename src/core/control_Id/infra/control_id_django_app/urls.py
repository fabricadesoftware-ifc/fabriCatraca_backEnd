from django.urls import include, path, reverse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.routers import DefaultRouter
from rest_framework import viewsets, status

from .views import (
    TemplateViewSet, TimeZoneViewSet, TimeSpanViewSet,
    AccessRuleViewSet, UserAccessRuleViewSet, AccessRuleTimeZoneViewSet,
    PortalViewSet, PortalAccessRuleViewSet, CardViewSet, AreaViewSet, 
    GroupViewSet, UserGroupsViewSet, GroupAccessRulesViewSet,
)
from .views.device import DeviceViewSet
from .views.sync import sync_all

router = DefaultRouter()
router.register(r'templates', TemplateViewSet)
router.register(r'time_zones', TimeZoneViewSet)
router.register(r'time_spans', TimeSpanViewSet)
router.register(r'access_rules', AccessRuleViewSet)
router.register(r'user_access_rules', UserAccessRuleViewSet)
router.register(r'access_rule_time_zones', AccessRuleTimeZoneViewSet)
router.register(r'portals', PortalViewSet)
router.register(r'portal_access_rules', PortalAccessRuleViewSet)
router.register(r'cards', CardViewSet)
router.register(r'devices', DeviceViewSet)
router.register(r'areas', AreaViewSet)
router.register(r'groups', GroupViewSet)
router.register(r'user_groups', UserGroupsViewSet)
router.register(r'group_access_rules', GroupAccessRulesViewSet)

@api_view(['GET'])
def control_id_root(request, format=None):
    return Response({
        'templates': reverse('template-list', request=request, format=format),
        'time_zones': reverse('timezone-list', request=request, format=format),
        'time_spans': reverse('timespan-list', request=request, format=format),
        'access_rules': reverse('accessrule-list', request=request, format=format),
        'user_access_rules': reverse('useraccessrule-list', request=request, format=format),
        'access_rule_time_zones': reverse('accessruletimezone-list', request=request, format=format),
        'portals': reverse('portal-list', request=request, format=format),
        'portal_access_rules': reverse('portalaccessrule-list', request=request, format=format),
        'cards': reverse('card-list', request=request, format=format),
        'devices': reverse('device-list', request=request, format=format),
        'areas': reverse('area-list', request=request, format=format),
        'groups': reverse('customgroup-list', request=request, format=format),
        'sync': reverse('sync-all', request=request, format=format),
        'user_groups': reverse('usergroup-list', request=request, format=format),
        'group_access_rules': reverse('groupaccessrule-list', request=request, format=format),
    })

urlpatterns = [
    path('', control_id_root, name='control_id-root'),
    path('sync/', sync_all, name='sync-all'),
    path('', include(router.urls)),
]