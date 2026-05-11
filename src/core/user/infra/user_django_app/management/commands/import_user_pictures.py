from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from src.core.control_id.infra.control_id_django_app.models import (
    CustomGroup,
    UserGroup,
)
from src.core.uploader.models import Archive
from src.core.user.infra.user_django_app.models import User

SUPPORTED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
ARCHIVE_UPLOAD_PREFIX = "user_pictures"
REPORT_FIELDS = [
    "group_name",
    "file_path",
    "status",
    "user_id",
    "user_name",
    "archive_id",
    "detail",
]


@dataclass(frozen=True)
class PictureImportRow:
    group_name: str
    file_path: str
    status: str
    user_id: int | None = None
    user_name: str = ""
    archive_id: int | None = None
    detail: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "group_name": self.group_name,
            "file_path": self.file_path,
            "status": self.status,
            "user_id": "" if self.user_id is None else str(self.user_id),
            "user_name": self.user_name,
            "archive_id": "" if self.archive_id is None else str(self.archive_id),
            "detail": self.detail,
        }


def normalize_match_key(value: str | None) -> str:
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKD", str(value))
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    normalized = normalized.lower()
    normalized = re.sub(r"[_\-.]+", " ", normalized)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def safe_storage_name(group_name: str, user: User, source_file: Path) -> str:
    group_slug = normalize_match_key(group_name).replace(" ", "_") or "sem_grupo"
    user_slug = normalize_match_key(user.name).replace(" ", "_") or f"user_{user.pk}"
    suffix = source_file.suffix.lower()
    return f"{ARCHIVE_UPLOAD_PREFIX}/{group_slug}/{user.pk}_{user_slug}{suffix}"


class Command(BaseCommand):
    help = (
        "Importa fotos de usuarios a partir de pastas de turmas. "
        "Por padrao roda em dry-run; use --commit para gravar."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "root_dir",
            help=(
                "Pasta raiz contendo uma pasta por turma/grupo. "
                "Ex: C:\\fotos\\1INFO1\\NOME DO ALUNO.jpg"
            ),
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Grava Archives e vincula as fotos aos usuarios. Sem isso apenas simula.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Substitui o vinculo de usuarios que ja possuem foto.",
        )
        parser.add_argument(
            "--allow-shared-minio",
            action="store_true",
            help=(
                "Permite gravar mesmo quando USE_MINIO_STORAGE=True. "
                "Use com cuidado se o MinIO local for o mesmo do deploy."
            ),
        )
        parser.add_argument(
            "--report",
            default="import_user_pictures_report.csv",
            help="Caminho do CSV de relatorio. Padrao: import_user_pictures_report.csv",
        )
        parser.add_argument(
            "--extensions",
            nargs="+",
            default=list(SUPPORTED_IMAGE_EXTENSIONS),
            help="Extensoes aceitas. Padrao: .jpg .jpeg .png .webp",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Mostra uma linha para cada arquivo processado.",
        )

    def handle(self, *args, **options):
        root_dir = Path(options["root_dir"]).expanduser().resolve()
        commit = bool(options["commit"])
        replace = bool(options["replace"])
        allow_shared_minio = bool(options["allow_shared_minio"])
        verbose = bool(options["verbose"])
        extensions = self._normalize_extensions(options["extensions"])
        report_path = Path(options["report"]).expanduser().resolve()

        if not root_dir.exists() or not root_dir.is_dir():
            raise CommandError(f"Pasta raiz nao encontrada: {root_dir}")

        self._guard_shared_storage(commit, allow_shared_minio)

        rows = list(
            self._process_root(
                root_dir=root_dir,
                commit=commit,
                replace=replace,
                extensions=extensions,
                verbose=verbose,
            )
        )
        self._write_report(report_path, rows)
        self._print_summary(rows, commit, report_path)

    def _normalize_extensions(self, extensions: list[str]) -> tuple[str, ...]:
        normalized = []
        for extension in extensions:
            extension = extension.strip().lower()
            if not extension:
                continue
            normalized.append(extension if extension.startswith(".") else f".{extension}")
        return tuple(normalized) or SUPPORTED_IMAGE_EXTENSIONS

    def _guard_shared_storage(self, commit: bool, allow_shared_minio: bool) -> None:
        if not commit:
            return

        uses_minio = bool(getattr(settings, "USE_MINIO_STORAGE", True))
        default_storage = str(getattr(settings, "DEFAULT_FILE_STORAGE", ""))
        uses_minio = uses_minio or "minio" in default_storage.lower()

        if uses_minio and not allow_shared_minio:
            raise CommandError(
                "Gravacao bloqueada: este ambiente parece usar MinIO. "
                "Rode primeiro sem --commit para validar. Se tiver certeza, use "
                "--commit --allow-shared-minio."
            )

    def _process_root(
        self,
        *,
        root_dir: Path,
        commit: bool,
        replace: bool,
        extensions: tuple[str, ...],
        verbose: bool,
    ) -> Iterable[PictureImportRow]:
        group_dirs = sorted(path for path in root_dir.iterdir() if path.is_dir())
        if not group_dirs:
            yield PictureImportRow(
                group_name="",
                file_path=str(root_dir),
                status="root_without_group_dirs",
                detail="Nenhuma pasta de turma/grupo encontrada.",
            )
            return

        for group_dir in group_dirs:
            yield from self._process_group_dir(
                group_dir=group_dir,
                commit=commit,
                replace=replace,
                extensions=extensions,
                verbose=verbose,
            )

    def _process_group_dir(
        self,
        *,
        group_dir: Path,
        commit: bool,
        replace: bool,
        extensions: tuple[str, ...],
        verbose: bool,
    ) -> Iterable[PictureImportRow]:
        group_name = group_dir.name.strip()
        group = CustomGroup.objects.filter(name__iexact=group_name).first()
        image_files = sorted(
            path
            for path in group_dir.iterdir()
            if path.is_file() and path.suffix.lower() in extensions
        )

        if not group:
            for image_file in image_files:
                row = PictureImportRow(
                    group_name=group_name,
                    file_path=str(image_file),
                    status="group_not_found",
                    detail=f"Grupo/turma '{group_name}' nao encontrado no banco.",
                )
                self._write_verbose(row, verbose)
                yield row
            return

        user_index = self._build_user_index(group)

        if not image_files:
            row = PictureImportRow(
                group_name=group_name,
                file_path=str(group_dir),
                status="group_without_images",
                detail="Nenhuma imagem suportada encontrada nesta pasta.",
            )
            self._write_verbose(row, verbose)
            yield row
            return

        for image_file in image_files:
            row = self._process_image_file(
                image_file=image_file,
                group=group,
                user_index=user_index,
                commit=commit,
                replace=replace,
            )
            self._write_verbose(row, verbose)
            yield row

    def _build_user_index(self, group: CustomGroup) -> dict[str, list[User]]:
        index: dict[str, list[User]] = {}
        relations = (
            UserGroup.objects.filter(group=group)
            .select_related("user")
            .order_by("user__name", "user_id")
        )
        for relation in relations:
            user = relation.user
            keys = {normalize_match_key(user.name), normalize_match_key(user.registration)}
            for key in keys:
                if key:
                    index.setdefault(key, []).append(user)
        return index

    def _process_image_file(
        self,
        *,
        image_file: Path,
        group: CustomGroup,
        user_index: dict[str, list[User]],
        commit: bool,
        replace: bool,
    ) -> PictureImportRow:
        match_key = normalize_match_key(image_file.stem)
        matches = user_index.get(match_key, [])

        if not matches:
            return PictureImportRow(
                group_name=group.name,
                file_path=str(image_file),
                status="user_not_found",
                detail=f"Nenhum usuario da turma bateu com '{image_file.stem}'.",
            )

        unique_matches = {user.pk: user for user in matches}
        if len(unique_matches) > 1:
            names = ", ".join(
                f"{user.pk} - {user.name}" for user in unique_matches.values()
            )
            return PictureImportRow(
                group_name=group.name,
                file_path=str(image_file),
                status="ambiguous_user",
                detail=f"Mais de um usuario encontrado: {names}",
            )

        user = next(iter(unique_matches.values()))

        if user.picture_id and not replace:
            return PictureImportRow(
                group_name=group.name,
                file_path=str(image_file),
                status="already_has_picture",
                user_id=user.pk,
                user_name=user.name,
                archive_id=user.picture_id,
                detail="Usuario ja possui foto. Use --replace para substituir o vinculo.",
            )

        if not commit:
            return PictureImportRow(
                group_name=group.name,
                file_path=str(image_file),
                status="would_import",
                user_id=user.pk,
                user_name=user.name,
                detail="Dry-run: foto seria importada e vinculada.",
            )

        archive = self._create_archive_for_user(user, group.name, image_file)
        return PictureImportRow(
            group_name=group.name,
            file_path=str(image_file),
            status="imported",
            user_id=user.pk,
            user_name=user.name,
            archive_id=archive.pk,
            detail="Foto importada e vinculada.",
        )

    def _create_archive_for_user(
        self, user: User, group_name: str, image_file: Path
    ) -> Archive:
        title = f"Foto usuario {user.pk} - {user.name}"
        storage_name = safe_storage_name(group_name, user, image_file)

        with transaction.atomic():
            archive = Archive(titulo=title)
            with image_file.open("rb") as handle:
                archive.arquivo.save(storage_name, File(handle), save=False)
                archive.save()

            user.picture = archive
            user.save(update_fields=["picture"])
            return archive

    def _write_report(self, report_path: Path, rows: list[PictureImportRow]) -> None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=REPORT_FIELDS)
            writer.writeheader()
            for row in rows:
                writer.writerow(row.as_dict())

    def _print_summary(
        self, rows: list[PictureImportRow], commit: bool, report_path: Path
    ) -> None:
        counts: dict[str, int] = {}
        for row in rows:
            counts[row.status] = counts.get(row.status, 0) + 1

        mode = "COMMIT" if commit else "DRY-RUN"
        self.stdout.write(self.style.SUCCESS(f"Importacao de fotos finalizada ({mode})."))
        for status_name in sorted(counts):
            self.stdout.write(f"{status_name}: {counts[status_name]}")
        self.stdout.write(f"Relatorio: {report_path}")

        if not commit:
            self.stdout.write(
                self.style.WARNING(
                    "Nada foi gravado. Rode novamente com --commit para importar."
                )
            )

    def _write_verbose(self, row: PictureImportRow, verbose: bool) -> None:
        if not verbose:
            return

        target = f" -> {row.user_id} - {row.user_name}" if row.user_id else ""
        self.stdout.write(f"[{row.status}] {row.file_path}{target}")
