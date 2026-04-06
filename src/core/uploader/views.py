from rest_framework import viewsets
from src.core.uploader.models import Archive
from src.core.uploader.serializers import ArchiveSerializer


class ArchiveViewSet(viewsets.ModelViewSet):
    """
    ViewSet para CRUD de Arquivos.
    - list, retrieve, create, update, destroy
    """

    queryset = Archive.objects.all().order_by("-criado_em")
    serializer_class = ArchiveSerializer
