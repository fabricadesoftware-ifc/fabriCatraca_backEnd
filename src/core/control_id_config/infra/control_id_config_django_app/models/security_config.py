from django.db import models
from src.core.control_Id.infra.control_id_django_app.models import Device


class SecurityConfig(models.Model):
    """Configuracoes de seguranca da catraca."""

    device = models.OneToOneField(
        Device,
        on_delete=models.CASCADE,
        related_name="security_config",
    )

    # Campos legados mantidos por compatibilidade com dados ja existentes.
    password_only = models.BooleanField(default=False, help_text="Aceitar apenas senha")
    hide_password_only = models.BooleanField(default=False, help_text="Ocultar entrada de senha")
    password_only_tip = models.CharField(max_length=255, blank=True, help_text="Dica para senha")
    hide_name_on_identification = models.BooleanField(default=False, help_text="Ocultar nome na identificação")
    denied_transaction_code = models.CharField(max_length=10, blank=True, help_text="Código para transação negada")
    send_code_when_not_identified = models.BooleanField(default=False, help_text="Enviar código quando não identificado")
    send_code_when_not_authorized = models.BooleanField(default=False, help_text="Enviar código quando não autorizado")

    # Campos efetivamente suportados pelo bloco `identifier` da catraca.
    verbose_logging_enabled = models.BooleanField(
        default=True,
        help_text="Habilita logs detalhados do identificador na catraca",
    )
    log_type = models.PositiveSmallIntegerField(
        default=1,
        help_text="Nivel de log retornado pelo bloco identifier da catraca",
    )
    multi_factor_authentication_enabled = models.BooleanField(
        default=False,
        help_text="Habilita autenticacao multifator no identificador",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração de Segurança"
        verbose_name_plural = "Configurações de Segurança"

    def __str__(self):
        return f"Configuracao de Seguranca - {self.device.name}"
