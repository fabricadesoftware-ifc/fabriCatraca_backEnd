import csv
import shutil
import uuid
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from src.core.control_id.infra.control_id_django_app.models import (
    CustomGroup,
    UserGroup,
)
from src.core.uploader.models import Archive


@pytest.fixture
def local_tmp_dir():
    path = Path.cwd() / "test-output" / f"import-user-pictures-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _write_fake_image(path):
    path.write_bytes(b"fake image bytes")


def _read_report(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.mark.django_db
def test_import_user_pictures_dry_run_does_not_create_archive(
    local_tmp_dir, user_factory
):
    group = CustomGroup.objects.create(name="1INFO1")
    user = user_factory(name="Ana Maria", registration="2026001")
    UserGroup.objects.create(user=user, group=group)

    group_dir = local_tmp_dir / "1INFO1"
    group_dir.mkdir()
    image_path = group_dir / "Ana Maria.jpg"
    _write_fake_image(image_path)
    report_path = local_tmp_dir / "report.csv"

    out = StringIO()
    call_command(
        "import_user_pictures",
        str(local_tmp_dir),
        "--report",
        str(report_path),
        stdout=out,
    )

    user.refresh_from_db()
    assert user.picture_id is None
    assert Archive.objects.count() == 0
    rows = _read_report(report_path)
    assert rows[0]["status"] == "would_import"
    assert rows[0]["user_id"] == str(user.pk)
    assert "Nada foi gravado" in out.getvalue()


@pytest.mark.django_db
@override_settings(USE_MINIO_STORAGE=False)
def test_import_user_pictures_commit_creates_archive(
    local_tmp_dir, user_factory, settings
):
    settings.MEDIA_ROOT = local_tmp_dir / "media"
    group = CustomGroup.objects.create(name="1INFO1")
    user = user_factory(name="Joao da Silva", registration="2026002")
    UserGroup.objects.create(user=user, group=group)

    group_dir = local_tmp_dir / "1INFO1"
    group_dir.mkdir()
    image_path = group_dir / "Joao da Silva.png"
    _write_fake_image(image_path)
    report_path = local_tmp_dir / "report.csv"

    call_command(
        "import_user_pictures",
        str(local_tmp_dir),
        "--commit",
        "--report",
        str(report_path),
    )

    user.refresh_from_db()
    assert user.picture_id is not None
    assert Archive.objects.count() == 1
    assert user.picture.arquivo.name.startswith("user_pictures/1info1/")
    rows = _read_report(report_path)
    assert rows[0]["status"] == "imported"
    assert rows[0]["archive_id"] == str(user.picture_id)


@pytest.mark.django_db
@override_settings(
    USE_MINIO_STORAGE=True,
    DEFAULT_FILE_STORAGE="minio_storage.storage.MinioMediaStorage",
)
def test_import_user_pictures_commit_blocks_shared_minio(
    local_tmp_dir, user_factory
):
    group = CustomGroup.objects.create(name="1INFO1")
    user = user_factory(name="Maria Souza", registration="2026003")
    UserGroup.objects.create(user=user, group=group)

    group_dir = local_tmp_dir / "1INFO1"
    group_dir.mkdir()
    _write_fake_image(group_dir / "Maria Souza.jpg")

    with pytest.raises(CommandError, match="MinIO"):
        call_command("import_user_pictures", str(local_tmp_dir), "--commit")

    user.refresh_from_db()
    assert user.picture_id is None
    assert Archive.objects.count() == 0
