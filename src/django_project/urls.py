from django.contrib import admin as django_admin
from django.urls import path, include
from django.conf import settings
from rest_framework.reverse import reverse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import redirect

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        'users': reverse('user-root', request=request, format=format),
        'control_id': reverse('control_id-root', request=request, format=format),
    })


django_admin.site.site_header = "Controle de Acesso Escolar"
django_admin.site.site_title = "Admin • Acesso Escolar"
django_admin.site.index_title = "Painel de Operações"

urlpatterns = [
    path('api/', api_root, name='api-root'),
    path('api/users/', include('src.core.user.infra.user_django_app.urls')),
    path('api/control_id/', include('src.core.control_Id.infra.control_id_django_app.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/admin/', django_admin.site.urls),
    path('', lambda request: redirect('api/', permanent=True)),
    
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
    
if settings.DEBUG:
    urlpatterns += [
        path("api/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    ]