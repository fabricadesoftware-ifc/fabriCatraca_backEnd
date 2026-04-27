import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.response import Response


@pytest.mark.integration
@pytest.mark.django_db
def test_import_users_returns_elapsed_time_on_success(api_client_admin, mocker):
    # Testa que a importacao informa a duracao total quando o processamento conclui com sucesso.
    mocker.patch(
        "src.core.control_id.infra.control_id_django_app.utils.import_users.time.perf_counter",
        side_effect=[10.0, 12.35],
    )
    mocker.patch(
        "src.core.control_id.infra.control_id_django_app.utils.import_users.ImportUsersView._save_upload",
        return_value=("C:/tmp/import.csv", "csv"),
    )
    mocker.patch(
        "src.core.control_id.infra.control_id_django_app.utils.import_users.ImportUsersView._get_import_profile",
        return_value="graduacao",
    )
    mocker.patch(
        "src.core.control_id.infra.control_id_django_app.utils.import_users.ImportUsersView._process_csv",
        return_value=Response(
            {"success": True, "message": "ok"},
            status=status.HTTP_200_OK,
        ),
    )
    unlink = mocker.patch(
        "src.core.control_id.infra.control_id_django_app.utils.import_users.os.unlink"
    )

    response = api_client_admin.post("/api/control_id/import_users/", {}, format="multipart")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    assert response.data["elapsed_s"] == 2.35
    unlink.assert_called_once_with("C:/tmp/import.csv")


@pytest.mark.integration
@pytest.mark.django_db
def test_import_users_returns_elapsed_time_on_validation_error(api_client_admin, mocker):
    # Testa que erros de upload tambem devolvem a duracao total medida pelo endpoint.
    mocker.patch(
        "src.core.control_id.infra.control_id_django_app.utils.import_users.time.perf_counter",
        side_effect=[20.0, 20.5],
    )

    response = api_client_admin.post("/api/control_id/import_users/", {}, format="multipart")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["error"] == "No file uploaded"
    assert response.data["elapsed_s"] == 0.5

@pytest.mark.integration
@pytest.mark.django_db
def test_import_users_csv_flow_executes_real_post_handler(api_client_admin, mocker):
    # Testa o fluxo real do POST CSV para garantir que a view ainda possui os metodos internos esperados.
    uploaded_file = SimpleUploadedFile(
        "usuarios.csv",
        b"registration,name\n2026001,Maria\n",
        content_type="text/csv",
    )
    parsed = mocker.Mock()
    parsed.rows = [mocker.Mock()]
    service = mocker.Mock()
    service.ensure_group.return_value = (mocker.Mock(name="grupo"), None)
    service.upsert_users.return_value = ([mocker.Mock()], [], 1, 0)
    service.sync_users_to_devices.return_value = [mocker.Mock()]
    service.create_local_relations.return_value = []

    mocker.patch(
        "src.core.control_id.infra.control_id_django_app.utils.import_users.parse_discente_csv",
        return_value=(parsed, None),
    )
    mocker.patch(
        "src.core.control_id.infra.control_id_django_app.utils.import_users.ImportUsersService",
        return_value=service,
    )

    response = api_client_admin.post(
        "/api/control_id/import_users/",
        {"file": uploaded_file, "import_profile": "graduacao"},
        format="multipart",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    assert response.data["rows_processed"] == 1
    assert "elapsed_s" in response.data
