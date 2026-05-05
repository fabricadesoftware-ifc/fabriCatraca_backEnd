from src.core.control_id_config.infra.control_id_config_django_app.views.easy_setup_engine import (
    _EasySetupEngine,
)
from src.core.control_id_config.infra.control_id_config_django_app.tasks import (
    _evaluate_easy_setup_report,
)


def _engine_for_device(device):
    engine = _EasySetupEngine()
    engine.set_device(device)
    return engine


def test_create_objects_safe_isolates_bad_entity_item_with_create_or_modify(
    mocker, make_response, device_factory
):
    engine = _engine_for_device(device_factory(name="Catraca Teste"))
    mocker.patch.object(engine, "login", return_value="session")

    values = [
        {"id": 1, "name": "Aluno 1"},
        {"id": 2, "name": "Aluno 2"},
        {"id": 3, "name": "Aluno quebrado"},
    ]

    def fake_post(url, json, timeout):
        ids = [value.get("id") for value in json["values"]]
        if "create_or_modify_objects.fcgi" in url and 3 in ids:
            return make_response(400, text='{"error":"bad id 3","code":1}')
        return make_response(200, text="{}")

    mocker.patch(
        "src.core.control_id_config.infra.control_id_config_django_app.views.easy_setup_engine.requests.post",
        side_effect=fake_post,
    )

    report = engine._create_objects_safe("users", values)

    assert report["ok"] is False
    assert report["applied"] == 2
    assert report["created"] == 0
    assert report["errors"] == 1
    assert report["initial_status"] == 400
    assert report["failed_items"][0]["item"]["id"] == 3
    assert any(stage["chunk_size"] == 1 for stage in report["stages"])


def test_create_objects_safe_uses_create_or_modify_for_entity_tables(
    mocker, make_response, device_factory
):
    engine = _engine_for_device(device_factory(name="Catraca Teste"))
    mocker.patch.object(engine, "login", return_value="session")
    post = mocker.patch(
        "src.core.control_id_config.infra.control_id_config_django_app.views.easy_setup_engine.requests.post",
        return_value=make_response(200, text="{}"),
    )

    report = engine._create_objects_safe(
        "access_rules",
        [{"id": 1, "name": "Livre", "type": 1, "priority": 0}],
    )

    assert report["ok"] is True
    assert report["strategy"] == "create_or_modify"
    assert report["applied"] == 1
    assert report["stages"] == []
    assert report["failed_items"] == []
    assert "create_or_modify_objects.fcgi" in post.call_args.args[0]


def test_create_objects_safe_skips_existing_junction_item(
    mocker, make_response, device_factory
):
    engine = _engine_for_device(device_factory(name="Catraca Teste"))
    mocker.patch.object(engine, "login", return_value="session")

    values = [
        {"user_id": 1, "group_id": 1},
        {"user_id": 2, "group_id": 1},
    ]

    def fake_post(url, json, timeout):
        user_ids = [value.get("user_id") for value in json["values"]]
        if "create_objects.fcgi" in url and 2 in user_ids:
            return make_response(
                400,
                text='{"error":"UNIQUE constraint failed: user_groups","code":1}',
            )
        return make_response(200, text="{}")

    post = mocker.patch(
        "src.core.control_id_config.infra.control_id_config_django_app.views.easy_setup_engine.requests.post",
        side_effect=fake_post,
    )

    report = engine._create_objects_safe("user_groups", values)

    assert report["ok"] is True
    assert report["created"] == 1
    assert report["skipped_unique"] == 1
    assert report["errors"] == 0
    assert report["failed_items"] == []
    assert all("create_or_modify_objects.fcgi" not in call.args[0] for call in post.mock_calls)


def test_create_objects_safe_reports_empty_tables_with_stable_shape(device_factory):
    engine = _engine_for_device(device_factory(name="Catraca Teste"))

    report = engine._create_objects_safe("cards", [])

    assert report == {
        "ok": True,
        "count": 0,
        "created": 0,
        "modified": 0,
        "skipped_unique": 0,
        "errors": 0,
        "note": "skipped",
        "strategy": "skipped",
        "chunk_plan": [],
        "stages": [],
        "failed_items": [],
        "failed_items_truncated": False,
        "skipped": True,
    }


def test_create_or_modify_fallback_only_descends_failed_chunks(
    mocker, make_response, device_factory
):
    engine = _engine_for_device(device_factory(name="Catraca Teste"))
    mocker.patch.object(engine, "login", return_value="session")
    values = [{"id": idx, "name": f"Aluno {idx}"} for idx in range(1, 107)]

    def fake_post(url, json, timeout):
        ids = [value["id"] for value in json["values"]]
        if "create_or_modify_objects.fcgi" in url and 42 in ids:
            return make_response(400, text='{"error":"bad id 42","code":1}')
        return make_response(200, text="{}")

    mocker.patch(
        "src.core.control_id_config.infra.control_id_config_django_app.views.easy_setup_engine.requests.post",
        side_effect=fake_post,
    )

    report = engine._create_objects_safe("users", values)

    assert report["ok"] is False
    assert report["applied"] == 105
    assert report["errors"] == 1
    assert report["failed_items"] == [
        {
            "table": "users",
            "item": {"id": 42, "name": "Aluno 42"},
            "status": 400,
            "detail": '{"error":"bad id 42","code":1}',
        }
    ]
    assert [
        (
            stage["chunk_size"],
            stage["records_ok"],
            stage["records_pending"],
        )
        for stage in report["stages"]
    ] == [
        (100, 6, 100),
        (50, 50, 50),
        (10, 40, 10),
        (5, 5, 5),
        (1, 4, 1),
    ]


def test_count_push_result_records_includes_partial_progress(device_factory):
    engine = _engine_for_device(device_factory(name="Catraca Teste"))

    assert (
        engine._count_push_result_records(
            {
                "ok": False,
                "count": 106,
                "applied": 105,
                "created": 0,
                "modified": 0,
                "skipped_unique": 0,
            }
        )
        == 105
    )
    assert engine._count_push_result_records({"ok": True, "count": 10}) == 10
    assert engine._count_push_result_records({"ok": True, "skipped": True}) == 0


def test_data_integrity_preflight_reports_duplicate_pins(mocker, device_factory):
    engine = _engine_for_device(device_factory(name="Catraca Teste"))
    mocker.patch.object(
        engine,
        "_load_active_pin_payloads",
        return_value=[
            {"user_id": 1, "name": "Aluno 1", "value": "1234"},
            {"user_id": 2, "name": "Aluno 2", "value": "1234"},
            {"user_id": 3, "name": "Aluno 3", "value": "5678"},
        ],
    )

    report = engine.validate_data_integrity()

    assert report["ok"] is False
    assert report["duplicate_pins"][0]["value"] == "1234"
    assert "PIN 1234" in report["error"]


def test_configure_device_settings_retries_without_unsupported_online_client(
    mocker, make_response, device_factory
):
    engine = _engine_for_device(device_factory(name="Catraca Teste"))
    payloads = []

    def fake_make_request(endpoint, json_data=None, **kwargs):
        payloads.append(dict(json_data or {}))
        if "online_client" in (json_data or {}):
            return make_response(
                400,
                text='{"error":"Node or attribute not found. Node path: config->modules->module[name=online_client]->param[name=enabled]","code":1}',
            )
        return make_response(200, text="{}")

    mocker.patch.object(engine, "_make_request", side_effect=fake_make_request)

    report = engine.configure_device_settings()

    assert report["ok"] is True
    assert report["online_client_skipped"] is True
    assert report["retry_without_online_client_status"] == 200
    assert "online_client" in payloads[0]
    assert "online_client" not in payloads[1]
    assert "general" in payloads[1]
    assert "identifier" in payloads[1]


def test_easy_setup_report_evaluation_ignores_missing_legacy_steps():
    report = {
        "steps": {
            "login": {"ok": True},
            "factory_reset": {"ok": True},
            "device_settings": {"ok": True},
            "datetime": {"ok": True},
            "monitor": {"ok": True},
            "push": {},
        }
    }

    status, failed_critical, warning_steps = _evaluate_easy_setup_report(report)

    assert status == "success"
    assert failed_critical == []
    assert warning_steps == []


def test_easy_setup_report_evaluation_treats_preflight_as_critical():
    report = {
        "steps": {
            "login": {"ok": True},
            "preflight": {"ok": False},
            "datetime": {"ok": True},
            "monitor": {"ok": True},
            "push": {},
        }
    }

    status, failed_critical, warning_steps = _evaluate_easy_setup_report(report)

    assert status == "failed"
    assert failed_critical == ["preflight"]
    assert warning_steps == []


def test_easy_setup_report_evaluation_keeps_legacy_steps_critical_when_present():
    report = {
        "steps": {
            "login": {"ok": True},
            "factory_reset": {"ok": True},
            "device_settings": {"ok": True},
            "disable_identifier": {"ok": False},
            "datetime": {"ok": True},
            "monitor": {"ok": True},
            "push": {},
        }
    }

    status, failed_critical, warning_steps = _evaluate_easy_setup_report(report)

    assert status == "failed"
    assert failed_critical == ["disable_identifier"]
    assert warning_steps == []
