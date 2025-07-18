from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import CustomUserManager






class User(AbstractUser):

    class UserType(models.IntegerChoices):
        VISITOR = 1 # Tem id

    
    username = None
    name = models.CharField(max_length=255)
    registration = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    user_type_id = models.IntegerField(choices=UserType.choices, null=True, blank=True, help_text="Visitantes terão id 1, usuarios cadastrados serão nulo")
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]
    EMAIL_FIELD = "email"
    
    objects = CustomUserManager()

    def __str__(self):
        return f"{self.id} - {self.name}"
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"