"""Retiros: escritura migrada, idempotencia, validaciones, vista desde Educación y Subsidios."""

import json
import time

import pytest
import requests

from conftest import AUDIT_LOG, EDUCACION, SUBSIDIOS, new_request_id

pytestmark = pytest.mark.writes


def retire(api, document, request_id, reason="retiro de prueba", consumer="subsidios"):
    return api.post("/api/v1/members/{0}/retirements".format(document),
                    {"requestId": request_id, "date": "2026-10-05", "reason": reason}, consumer=consumer)


def test_retirement_is_created_and_visible_in_legacy(api, legacy, retirable):
    document, created = retirable
    request_id = new_request_id()
    created.append(request_id)
    response = retire(api, document, request_id)
    assert response.status_code == 201
    assert response.json()["status"] == "APPLIED" and response.json()["movementId"]
    assert legacy.status_of(document) == "R"
    assert legacy.retirement_rows(document) == 1
    assert api.get("/api/v1/members/" + document).json()["status"] == "RETIRED"


def test_education_sees_the_retirement_made_through_the_gateway(api, retirable):
    document, created = retirable
    request_id = new_request_id()
    created.append(request_id)
    assert retire(api, document, request_id).status_code == 201
    view = requests.get("{0}/afiliados/{1}".format(EDUCACION, document), timeout=10).json()
    assert view["estado"] == "RETIRADO"


def test_same_request_id_does_not_duplicate(api, legacy, retirable):
    document, created = retirable
    request_id = new_request_id()
    created.append(request_id)
    first = retire(api, document, request_id)
    second = retire(api, document, request_id)
    third = retire(api, document, request_id)
    assert (first.status_code, second.status_code, third.status_code) == (201, 200, 200)
    assert first.json()["movementId"] == second.json()["movementId"] == third.json()["movementId"]
    assert legacy.retirement_rows(document) == 1


def test_request_id_reused_for_another_member_is_a_conflict(api, legacy, retirable):
    document, created = retirable
    request_id = new_request_id()
    created.append(request_id)
    assert retire(api, document, request_id).status_code == 201
    other = retire(api, "0000000001", request_id)
    assert other.status_code == 409
    assert legacy.retirement_rows(document) == 1


def test_retirement_of_unknown_member_is_404_and_leaves_no_trace(api):
    request_id = new_request_id()
    assert retire(api, "0000000001", request_id).status_code == 404
    assert api.get("/api/v1/retirements/" + request_id).status_code == 404


@pytest.mark.parametrize("body", [{}, {"requestId": "ok"}, {"requestId": "ok", "date": "2026-13-45"},
                                  {"requestId": "con espacios", "date": "2026-10-05"}, {"requestId": "ok", "date": "2026-10-05", "reason": "x" * 201}])
def test_invalid_retirement_bodies_are_400(api, body):
    response = api.post("/api/v1/members/1/retirements", body)
    assert response.status_code == 400
    assert response.json()["error_id"]


def test_retirement_status_can_be_queried(api, retirable):
    document, created = retirable
    request_id = new_request_id()
    created.append(request_id)
    retire(api, document, request_id)
    body = api.get("/api/v1/retirements/" + request_id).json()
    assert body["status"] == "APPLIED" and body["requestId"] == request_id


def test_legacy_procedure_still_works_independently(legacy, retirable):
    document, _ = retirable
    movement = legacy.query("SELECT sp_registrar_retiro(%s, DATE '2026-10-05', 'camino legacy', 'PRUEBA')", (document,), commit=True)[0][0]
    assert movement and legacy.status_of(document) == "R"
    assert legacy.retirement_rows(document) == 1


def read_audit():
    with open(AUDIT_LOG, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle.read().splitlines() if line.strip()]


def test_subsidios_registers_through_the_gateway_once(api, legacy, retirable):
    document, created = retirable
    body = {"documento": document, "fecha": "2026-10-06", "motivo": "retiro vía subsidios"}
    first = requests.post(SUBSIDIOS + "/retiros", json=body, timeout=15)
    second = requests.post(SUBSIDIOS + "/retiros", json=body, timeout=15)
    assert first.status_code == 201 and first.json()["via"] == "gateway"
    assert second.status_code == 200 and second.json()["movimiento"] == first.json()["movimiento"]
    created.append(first.json()["requestId"])
    assert legacy.retirement_rows(document) == 1
    masked_tail = document[-4:]
    entries = [e for e in read_audit() if e["consumer"] == "subsidios" and e["endpoint"].endswith(masked_tail + "/retirements")]
    assert len(entries) >= 2


def test_subsidios_unknown_member_is_404():
    response = requests.post(SUBSIDIOS + "/retiros", json={"documento": "0000000001", "fecha": "2026-10-06"}, timeout=15)
    assert response.status_code == 404


def test_audit_log_has_required_fields_and_masks_documents(api, sample_member):
    api.get("/api/v1/members/" + sample_member, consumer="mobile")
    time.sleep(0.2)
    entries = read_audit()[-50:]
    assert entries
    for entry in entries:
        assert {"timestamp", "consumer", "endpoint", "status", "latency_ms"} <= set(entry)
        assert entry["consumer"] in ("portal", "subsidios", "mobile", "anonymous")
    assert not any(sample_member in json.dumps(e) for e in entries)
    assert any(e["consumer"] == "mobile" and e["endpoint"].endswith(sample_member[-4:]) for e in entries)


def test_stats_endpoint_exposes_queue_and_circuit(api):
    body = api.get("/api/v1/ops/stats", consumer="mobile").json()
    assert body["circuit"] in ("OPEN", "CLOSED")
    assert set(body["retirements"]) >= {"PENDING", "APPLIED", "FAILED"}
