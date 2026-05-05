from datetime import date
from io import BytesIO
import os
import tempfile

import pandas as pd
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.response import Response

from src.core.control_id.infra.control_id_django_app.utils.excel_parser import (
    parse_sheet,
    parse_sheet_name,
)


def _build_excel_file(sheets: dict[str, pd.DataFrame]) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, dataframe in sheets.items():
            dataframe.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output.read()


@pytest.mark.parametrize(
    ("sheet_name", "expected_group_name"),
    [
        ("1INFO1(2026)", "1INFO1"),
        ("1INFO1", "1INFO1"),
        ("2QUIMI", "2QUIMI"),
    ],
)
def test_parse_sheet_name_accepts_current_technical_formats(
    sheet_name, expected_group_name
):
    assert parse_sheet_name(sheet_name) == expected_group_name


def test_parse_sheet_accepts_technical_workbook_layout():
    dataframe = pd.DataFrame(
        {
            "matricula": ["2026317880"],
            "nome": ["ANANDA FUSINATO"],
            "fone": ["47 98871-4585"],
            "datanascimento": ["2010-10-22"],
            "celular": ["47 99195-0170"],
            "pai": ["LUCIANO FUSINATO"],
            "mae": ["ALLYNE DEUNIZIO"],
        }
    )
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx",
        dir=os.getcwd(),
        delete=False,
    ) as workbook_file:
        workbook_file.write(_build_excel_file({"1INFO1": dataframe}))
        workbook_path = workbook_file.name

    try:
        parsed, error = parse_sheet(workbook_path, "1INFO1")
    finally:
        if os.path.exists(workbook_path):
            os.unlink(workbook_path)

    assert error is None
    assert parsed is not None
    assert parsed.group_name == "1INFO1"
    assert len(parsed.rows) == 1
    assert parsed.rows[0].registration == "2026317880"
    assert parsed.rows[0].name == "ANANDA FUSINATO"
    assert parsed.rows[0].birth_date == date(2010, 10, 22)
    assert parsed.rows[0].phone == "47 99195-0170"
    assert parsed.rows[0].phone_landline == "47 98871-4585"


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


@pytest.mark.integration
@pytest.mark.django_db
def test_import_users_excel_accepts_technical_workbook_layout(api_client_admin, mocker):
    uploaded_file = SimpleUploadedFile(
        "Alunos Tecnico 2026.xlsx",
        _build_excel_file(
            {
                "1INFO1": pd.DataFrame(
                    {
                        "matricula": ["2026317880"],
                        "nome": ["ANANDA FUSINATO"],
                        "fone": ["47 98871-4585"],
                        "datanascimento": ["2010-10-22"],
                        "celular": ["47 99195-0170"],
                        "pai": ["LUCIANO FUSINATO"],
                        "mae": ["ALLYNE DEUNIZIO"],
                    }
                ),
                "2QUIMI": pd.DataFrame(
                    {
                        "matricula": ["2025321969"],
                        "nome": ["ADRYA VAZ DE SOUZA"],
                        "fone": ["47 99248-3695"],
                        "datanascimento": ["2009-10-07"],
                        "celular": ["47 99248-3695"],
                        "pai": ["MANOEL VAGNER DE SOUZA"],
                        "mae": ["MARTILENE CRISTO VAZ"],
                    }
                ),
            }
        ),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    service = mocker.Mock()
    fake_group = mocker.Mock()
    service.ensure_group.return_value = (fake_group, None)
    service.upsert_users.return_value = ([mocker.Mock()], [], 1, 0)
    service.sync_users_to_devices.return_value = [mocker.Mock()]
    service.create_local_relations.return_value = []

    mocker.patch(
        "src.core.control_id.infra.control_id_django_app.utils.import_users.ImportUsersService",
        return_value=service,
    )

    response = api_client_admin.post(
        "/api/control_id/import_users/",
        {"file": uploaded_file, "import_profile": "tecnico_integrado"},
        format="multipart",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    assert response.data["sheets_processed"] == 2
    assert "Usuários: 2 criados, 0 atualizados." in response.data["message"]
    assert service.upsert_users.call_count == 2
    assert [call.args[0] for call in service.ensure_group.call_args_list] == [
        "1INFO1",
        "2QUIMI",
    ]
