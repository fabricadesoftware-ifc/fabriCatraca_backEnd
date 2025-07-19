from django.db import models

class Device(models.Model):
    name = models.CharField(max_length=255, help_text="Nome descritivo do equipamento")
    ip = models.CharField(max_length=255, help_text="IP ou hostname do equipamento. Ex: 192.168.0.129")
    username = models.CharField(max_length=255, help_text="Usuário para autenticação")
    password = models.CharField(max_length=255, help_text="Senha para autenticação")
    is_active = models.BooleanField(default=True, help_text="Se o dispositivo está ativo para sincronização")
    is_default = models.BooleanField(default=False, help_text="Se é o dispositivo padrão quando nenhum é especificado")
    users = models.ManyToManyField('user_django_app.User', related_name='devices', blank=True)

    class Meta:
        verbose_name = "Dispositivo"
        verbose_name_plural = "Dispositivos"
        db_table = "control_id_device"

    def __str__(self):
        return f"{self.name} ({self.ip})"

    def save(self, *args, **kwargs):
        # Se este dispositivo está sendo marcado como padrão
        if self.is_default:
            # Remove o status de padrão de outros dispositivos
            Device.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs) 