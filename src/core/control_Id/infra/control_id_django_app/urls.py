from django.urls import include, path, reverse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.routers import DefaultRouter
from rest_framework import viewsets, status

from .views import CatracaViewSet

router = DefaultRouter()
router.register(r'control_id', CatracaViewSet, basename='control_id')


@api_view(['GET'])
def authentication_root(request, format=None):
    return Response({
        'control_id': reverse('control_id-list', request=request, format=format),
    })

urlpatterns = [
    path('', authentication_root, name='control_id-root'),
    path('', include(router.urls)),
]