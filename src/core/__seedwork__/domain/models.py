from django.db import models
from safedelete.models import SafeDeleteModel
from safedelete.config import SOFT_DELETE_CASCADE


class BaseModel(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta(SafeDeleteModel.Meta):
        abstract = True
