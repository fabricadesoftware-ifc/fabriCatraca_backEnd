from django.db import models
from minio_storage.storage import MinioMediaStorage

class Archive(models.Model):
    titulo = models.CharField(max_length=200)
    arquivo = models.FileField(storage=MinioMediaStorage)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo
