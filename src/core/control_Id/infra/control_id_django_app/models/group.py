from django.db import models
from django.contrib.auth.models import Group

class CustomGroup(Group):
    class Meta:
        proxy = True
        verbose_name = "Grupo"
        verbose_name_plural = "Grupos"
        
    def __str__(self):
        return self.name
    
    