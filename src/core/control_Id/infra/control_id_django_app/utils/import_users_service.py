import logging
from dataclasses import dataclass

from django.contrib.auth.models import Group as DjangoGroup
from django.db import transaction
from rest_framework import status

from src.core.__seedwork__.infra import ControlIDSyncMixin
from src.core.control_Id.infra.control_id_django_app.models import (
    CustomGroup as Group,
    UserGroup,
)
from src.core.control_Id.infra.control_id_django_app.models.device import Device
from src.core.user.infra.user_django_app.models import User
from src.core.user.infra.user_django_app.validate import normalize_phone
from .excel_parser import ParsedRow

logger = logging.getLogger(__name__)


@dataclass
class SheetImportResult:
    created_users: int = 0
    updated_users: int = 0
    created_groups: int = 0
    updated_groups: int = 0
    created_relations: int = 0
    errors: list[str] | None = None
    catraca_errors: list[str] | None = None

    def __post_init__(self):
        self.errors = self.errors or []
        self.catraca_errors = self.catraca_errors or []


class ImportUsersService(ControlIDSyncMixin):
    """Serviço de importação de usuários para o Django e catracas."""

    def __init__(self):
        super().__init__()
        self._device = None

    def _build_user_payload(self, user: User) -> dict:
        payload = {
            "id": user.pk,
            "name": user.name,
            "registration": user.registration,
        }
        return payload

    def _normalize_phone_or_none(self, value: str | None) -> str | None:
        if not value:
            return None
        try:
            return normalize_phone(value)
        except ValueError:
            logger.warning("[USER] Telefone ignorado por formato invalido: %s", value)
            return None

    def _get_available_email(self, email: str | None, user: User | None = None) -> str | None:
        if not email:
            return None

        email = email.strip().lower()
        queryset = User.objects.filter(email=email)
        if user and user.pk:
            queryset = queryset.exclude(pk=user.pk)

        if queryset.exists():
            logger.warning("[USER] E-mail '%s' ignorado porque ja esta em uso", email)
            return None
        return email

    # ── Grupo ──

    def _sync_group_to_devices(self, group: DjangoGroup) -> tuple[bool, str | None]:
        """Upsert do grupo em todas as catracas ativas."""
        try:
            devices = list(Device.objects.filter(is_active=True))
            if not devices:
                return False, "Nenhuma catraca ativa encontrada"

            self._device = None
            logger.info(
                f"[GRUPO] Sincronizando id={group.pk} name='{group.name}' "
                f"→ {len(devices)} device(s)"
            )

            response = self.create_or_update_objects_in_all_devices(
                "groups", [{"id": group.pk, "name": group.name}]
            )

            if response.status_code != status.HTTP_200_OK:
                error_detail = getattr(response, "data", str(response))
                logger.error(f"[GRUPO] Falha id={group.pk} name='{group.name}': {error_detail}")
                return False, f"Erro ao sincronizar grupo na catraca: {error_detail}"

            logger.info(f"[GRUPO] OK id={group.pk} name='{group.name}'")
            return True, None

        except Exception as e:
            logger.exception(f"[GRUPO] Exceção id={group.pk} name='{group.name}': {e}")
            return False, str(e)

    def ensure_group(self, group_name: str) -> tuple[DjangoGroup | None, str | None]:
        """
        Garante que o grupo existe no Django e em todas as catracas.
        Retorna (grupo, erro).
        """
        self._device = None
        grupo = Group.objects.filter(name=group_name).first()

        if not grupo:
            logger.info(f"[GRUPO] '{group_name}' não existe — criando localmente")
            sp = transaction.savepoint()
            try:
                grupo = Group.objects.create(name=group_name)
                logger.info(f"[GRUPO] Criado localmente: id={grupo.pk}")
            except Exception as e:
                transaction.savepoint_rollback(sp)
                logger.exception(f"[GRUPO] Falha ao criar '{group_name}' localmente: {e}")
                return None, str(e)
        else:
            logger.info(f"[GRUPO] '{group_name}' já existe localmente (id={grupo.pk})")
            sp = transaction.savepoint()

        success, err = self._sync_group_to_devices(grupo)
        if not success:
            transaction.savepoint_rollback(sp)
            logger.error(f"[GRUPO] Rollback de '{group_name}' após falha na catraca: {err}")
            return None, err

        transaction.savepoint_commit(sp)
        return grupo, None

    # ── Usuários ──

    def upsert_users(
        self, rows: list[ParsedRow], app_role: str | None = None
    ) -> tuple[list[User], list[User], int, int]:
        """
        Cria ou atualiza usuários no Django.
        Retorna (novos, existentes, qtd_criados, qtd_atualizados).
        """
        users_new: list[User] = []
        users_existing: list[User] = []

        for row in rows:
            user = User.objects.filter(registration=row.registration).first()
            phone = self._normalize_phone_or_none(row.phone)
            phone_landline = self._normalize_phone_or_none(row.phone_landline)

            if not user:
                email = self._get_available_email(row.email)
                user = User.objects.create(
                    id=row.registration,
                    name=row.name,
                    registration=row.registration,
                    email=email,
                    birth_date=row.birth_date,
                    phone=phone,
                    phone_landline=phone_landline,
                    app_role=app_role or User.AppRole.ALUNO,
                    is_active=True,
                )
                logger.info(
                    f"[USER] Criado: id={user.pk} "
                    f"name='{user.name}' registration={user.registration}"
                )
                users_new.append(user)
            else:
                update_fields = []

                if user.name != row.name:
                    user.name = row.name
                    update_fields.append("name")
                if user.registration != row.registration:
                    user.registration = row.registration
                    update_fields.append("registration")
                if not user.is_active:
                    user.is_active = True
                    update_fields.append("is_active")
                if app_role and user.app_role != app_role:
                    user.app_role = app_role
                    update_fields.append("app_role")
                if row.birth_date and user.birth_date != row.birth_date:
                    user.birth_date = row.birth_date
                    update_fields.append("birth_date")
                if phone and user.phone != phone:
                    user.phone = phone
                    update_fields.append("phone")
                if phone_landline and user.phone_landline != phone_landline:
                    user.phone_landline = phone_landline
                    update_fields.append("phone_landline")

                email = self._get_available_email(row.email, user)
                if email and user.email != email:
                    user.email = email
                    update_fields.append("email")
                if update_fields:
                    logger.info(f"[USER] Atualizado: id={user.pk} '{user.name}' → '{row.name}'")
                    user.save(update_fields=update_fields)
                else:
                    logger.info(f"[USER] Sem alterações: id={user.pk} name='{user.name}'")
                users_existing.append(user)

        return users_new, users_existing, len(users_new), len(users_existing)

    def sync_users_to_devices(
        self, users: list[User], sheet_name: str
    ) -> list[User]:
        """Upsert em batch dos usuários em todas as catracas."""
        if not users:
            return []

        self._device = None
        batch_payload = [self._build_user_payload(u) for u in users]

        logger.info(
            f"[USERS] Batch upsert de {len(batch_payload)} usuário(s) "
            f"ids={[p['id'] for p in batch_payload]}"
        )

        response = self.create_or_update_objects_in_all_devices("users", batch_payload)

        logger.info(
            f"[USERS] Resposta batch: status={response.status_code} "
            f"data={getattr(response, 'data', None)}"
        )

        if response.status_code != status.HTTP_200_OK:
            error_detail = getattr(response, "data", str(response))
            logger.error(f"[USERS] Falha batch aba '{sheet_name}': {error_detail}")
            return []

        logger.info(f"[USERS] {len(users)} usuário(s) confirmado(s) na catraca")
        return users

    # ── Relações user_group ──

    def create_local_relations(
        self, users: list[User], grupo: DjangoGroup
    ) -> list[User]:
        """Cria relações UserGroup locais. Retorna apenas os users com relação nova."""
        new_relation_users = []
        for user in users:
            _, created = UserGroup.objects.get_or_create(user=user, group=grupo)
            if created:
                new_relation_users.append(user)

        logger.info(
            f"[RELACAO] {len(new_relation_users)} nova(s) relação(ões) "
            f"para grupo '{grupo.name}'"
        )
        return new_relation_users

    def sync_relations_to_devices(
        self, users: list[User], grupo: DjangoGroup, sheet_name: str
    ) -> bool:
        """Upsert em batch das relações user_groups em todas as catracas."""
        if not users:
            return True

        self._device = None
        relations_payload = [
            {"user_id": u.pk, "group_id": grupo.pk} for u in users
        ]

        logger.info(
            f"[RELACAO] Batch upsert de {len(relations_payload)} relação(ões) "
            f"grupo id={grupo.pk} name='{grupo.name}'"
        )

        response = self.create_or_update_objects_in_all_devices(
            "user_groups", relations_payload
        )

        logger.info(
            f"[RELACAO] Resposta batch: status={response.status_code} "
            f"data={getattr(response, 'data', None)}"
        )

        if response.status_code != status.HTTP_200_OK:
            error_detail = getattr(response, "data", str(response))
            logger.error(f"[RELACAO] Falha batch aba '{sheet_name}': {error_detail}")
            return False

        return True
