import logging
from dataclasses import dataclass
from typing import Any, Generic, Iterable, TypeVar

from django.contrib.auth.models import Group as DjangoGroup
from django.db import transaction
from rest_framework import status

from src.core.__seedwork__.infra import ControlIDSyncMixin
from src.core.__seedwork__.infra.catraca_sync import CatracaSyncError
from src.core.control_id.infra.control_id_django_app.models import (
    CustomGroup as Group,
    UserGroup,
)
from src.core.control_id.infra.control_id_django_app.models.device import Device
from src.core.user.infra.user_django_app.models import User
from src.core.user.infra.user_django_app.validate import normalize_phone
from .excel_parser import ParsedRow

logger = logging.getLogger(__name__)

IMPORT_SYNC_CHUNK_LADDER = (100, 50, 10, 5, 1)
MAX_IMPORT_SYNC_FAILURE_MESSAGES = 20

T = TypeVar("T")


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


@dataclass(frozen=True)
class ImportSyncItem(Generic[T]):
    source: T
    payload: dict[str, Any]
    label: str


@dataclass(frozen=True)
class ImportSyncFailure:
    object_name: str
    label: str
    payload: dict[str, Any]
    status_code: int | None
    detail: str

    def to_message(self) -> str:
        status_label = f"HTTP {self.status_code}" if self.status_code else "sem HTTP"
        return (
            f"{self.object_name}: {self.label} falhou na catraca "
            f"({status_label}) - {self.detail}"
        )


@dataclass(frozen=True)
class ImportSyncResult(Generic[T]):
    object_name: str
    attempted_count: int
    successful_items: list[T]
    failures: list[ImportSyncFailure]

    @property
    def synced_count(self) -> int:
        return len(self.successful_items)

    @property
    def failed_count(self) -> int:
        return len(self.failures)

    @property
    def ok(self) -> bool:
        return self.failed_count == 0


class ImportUsersService(ControlIDSyncMixin):
    """Serviço de importação de usuários para o Django e catracas."""

    def __init__(self):
        super().__init__()
        self._device = None
        self.last_sync_failures: list[ImportSyncFailure] = []

    def _chunk_items(
        self, items: list[ImportSyncItem[T]], chunk_size: int
    ) -> Iterable[list[ImportSyncItem[T]]]:
        for index in range(0, len(items), chunk_size):
            yield items[index : index + chunk_size]

    def _try_sync_chunk(
        self,
        object_name: str,
        items: list[ImportSyncItem[T]],
    ) -> tuple[bool, int | None, str | None]:
        values = [item.payload for item in items]
        try:
            response = self.create_or_update_objects_in_all_devices(
                object_name,
                values,
            )
        except CatracaSyncError as exc:
            return False, exc.status_code, str(exc)
        except Exception as exc:
            logger.exception("[IMPORT_SYNC] Excecao ao sincronizar %s", object_name)
            return False, None, str(exc)

        if response.status_code == status.HTTP_200_OK:
            return True, response.status_code, None

        detail = getattr(response, "data", str(response))
        return False, response.status_code, str(detail)

    def _sync_items_with_dynamic_chunks(
        self,
        object_name: str,
        items: list[ImportSyncItem[T]],
        source_name: str,
    ) -> ImportSyncResult[T]:
        """
        Sincroniza como no Easy Setup: lote completo, depois 100/50/10/5/1.
        """
        self.last_sync_failures = []

        if not items:
            return ImportSyncResult(
                object_name=object_name,
                attempted_count=0,
                successful_items=[],
                failures=[],
            )

        logger.info(
            "[IMPORT_SYNC] %s: tentando lote completo de %s item(ns) da origem '%s'",
            object_name,
            len(items),
            source_name,
        )
        ok, initial_status, initial_detail = self._try_sync_chunk(object_name, items)
        if ok:
            logger.info(
                "[IMPORT_SYNC] %s: lote completo sincronizado (%s item(ns))",
                object_name,
                len(items),
            )
            return ImportSyncResult(
                object_name=object_name,
                attempted_count=len(items),
                successful_items=[item.source for item in items],
                failures=[],
            )

        logger.warning(
            "[IMPORT_SYNC] %s: lote completo da origem '%s' falhou "
            "(HTTP %s). Iniciando fallback dinamico: 100, 50, 10, 5, 1. Detalhe: %s",
            object_name,
            source_name,
            initial_status,
            initial_detail,
        )

        pending = list(items)
        successful_items: list[T] = []
        failures: list[ImportSyncFailure] = []

        for chunk_size in IMPORT_SYNC_CHUNK_LADDER:
            if not pending:
                break

            next_pending: list[ImportSyncItem[T]] = []
            logger.info(
                "[IMPORT_SYNC] %s: tentando %s item(ns) pendente(s) em blocos de %s",
                object_name,
                len(pending),
                chunk_size,
            )

            for chunk in self._chunk_items(pending, chunk_size):
                ok, chunk_status, chunk_detail = self._try_sync_chunk(
                    object_name,
                    chunk,
                )
                if ok:
                    successful_items.extend(item.source for item in chunk)
                    logger.info(
                        "[IMPORT_SYNC] %s: bloco de %s item(ns) OK",
                        object_name,
                        len(chunk),
                    )
                    continue

                if chunk_size == 1:
                    failed_item = chunk[0]
                    failure = ImportSyncFailure(
                        object_name=object_name,
                        label=failed_item.label,
                        payload=failed_item.payload,
                        status_code=chunk_status,
                        detail=str(chunk_detail)[:500],
                    )
                    failures.append(failure)
                    logger.error("[IMPORT_SYNC] %s", failure.to_message())
                    continue

                next_pending.extend(chunk)

            pending = next_pending

        successful_source_ids = {id(source) for source in successful_items}
        ordered_successful_items = [
            item.source for item in items if id(item.source) in successful_source_ids
        ]

        result = ImportSyncResult(
            object_name=object_name,
            attempted_count=len(items),
            successful_items=ordered_successful_items,
            failures=failures,
        )
        self.last_sync_failures = failures
        logger.info(
            "[IMPORT_SYNC] %s: finalizado origem '%s' - %s/%s OK, %s falha(s)",
            object_name,
            source_name,
            result.synced_count,
            result.attempted_count,
            result.failed_count,
        )
        return result

    def get_last_sync_failure_messages(self) -> list[str]:
        return [
            failure.to_message()
            for failure in self.last_sync_failures[:MAX_IMPORT_SYNC_FAILURE_MESSAGES]
        ]

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

    def _get_available_email(
        self, email: str | None, user: User | None = None
    ) -> str | None:
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
                logger.error(
                    f"[GRUPO] Falha id={group.pk} name='{group.name}': {error_detail}"
                )
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
                logger.exception(
                    f"[GRUPO] Falha ao criar '{group_name}' localmente: {e}"
                )
                return None, str(e)
        else:
            logger.info(f"[GRUPO] '{group_name}' já existe localmente (id={grupo.pk})")
            sp = transaction.savepoint()

        success, err = self._sync_group_to_devices(grupo)
        if not success:
            transaction.savepoint_rollback(sp)
            logger.error(
                f"[GRUPO] Rollback de '{group_name}' após falha na catraca: {err}"
            )
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
                    logger.info(
                        f"[USER] Atualizado: id={user.pk} '{user.name}' → '{row.name}'"
                    )
                    user.save(update_fields=update_fields)
                else:
                    logger.info(
                        f"[USER] Sem alterações: id={user.pk} name='{user.name}'"
                    )
                users_existing.append(user)

        return users_new, users_existing, len(users_new), len(users_existing)

    def sync_users_to_devices(self, users: list[User], sheet_name: str) -> list[User]:
        """Upsert em batch dos usuarios em todas as catracas."""
        if not users:
            self.last_sync_failures = []
            return []

        self._device = None
        items = [
            ImportSyncItem(
                source=user,
                payload=self._build_user_payload(user),
                label=f"usuario id={user.pk} name='{user.name}'",
            )
            for user in users
        ]
        result = self._sync_items_with_dynamic_chunks(
            "users",
            items,
            sheet_name,
        )

        logger.info(
            "[USERS] Aba '%s': %s/%s usuario(s) confirmado(s) na catraca",
            sheet_name,
            result.synced_count,
            result.attempted_count,
        )
        return result.successful_items

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
        """Upsert em batch das relacoes user_groups em todas as catracas."""
        if not users:
            self.last_sync_failures = []
            return True

        self._device = None
        items = [
            ImportSyncItem(
                source=user,
                payload={"user_id": user.pk, "group_id": grupo.pk},
                label=(
                    f"relacao user_id={user.pk} group_id={grupo.pk} "
                    f"group='{grupo.name}'"
                ),
            )
            for user in users
        ]
        result = self._sync_items_with_dynamic_chunks(
            "user_groups",
            items,
            sheet_name,
        )

        logger.info(
            "[RELACAO] Aba '%s': %s/%s relacao(oes) confirmada(s) na catraca",
            sheet_name,
            result.synced_count,
            result.attempted_count,
        )
        return result.ok
