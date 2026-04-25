from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from minio_storage.storage import MinioMediaStorage
from src.core.__seedwork__.domain.models import BaseModel


def archive_storage():
    if getattr(settings, "USE_MINIO_STORAGE", True):
        return MinioMediaStorage()
    return FileSystemStorage()


class Archive(BaseModel):
    titulo = models.CharField(max_length=200)
    arquivo = models.FileField(storage=archive_storage)
    # criado_em removido, use created_at do BaseModel

    class Meta(BaseModel.Meta):
        verbose_name = "Arquivo"
        verbose_name_plural = "Arquivos"

    def __str__(self):
        return self.titulo
