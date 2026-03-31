from django.urls import include, path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.routers import DefaultRouter

from .views import ArchiveViewSet
router = DefaultRouter()
router.register(r'archives', ArchiveViewSet, basename='archive')



@api_view(["GET"])
def uploader_root(request, format=None):
    return Response(
        {
            "uploader": reverse("archive-list", request=request, format=format),
        }
    )


urlpatterns = [
    path("", uploader_root, name="uploader-root"),
    path("", include(router.urls)),
]
