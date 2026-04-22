from django.urls import include, path, reverse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.routers import DefaultRouter

from .views import UserViewSet, VisitasViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'visitas', VisitasViewSet, basename='visitas')


@api_view(['GET'])
def authentication_root(request, format=None):
    return Response({
        'users': reverse('user-list', request=request, format=format),
        'visitas': reverse('visitas-list', request=request, format=format),
    })

urlpatterns = [
    path('', authentication_root, name='user-root'),
    path('', include(router.urls)),
]
