"""Autenticación, privilegios y manejo uniforme de errores."""

import pytest

from conftest import GATEWAY, new_request_id

PROTECTED = ["/api/v1/members/1", "/api/v1/members/1/beneficiaries", "/api/v1/companies/2001",
             "/api/v1/migration/status", "/api/v1/ops/stats"]


@pytest.mark.parametrize("path", PROTECTED)
def test_requests_without_token_get_401(api, path):
    response = api.get(path, consumer=None)
    assert response.status_code == 401
    assert response.json()["error_id"]


def test_invalid_token_gets_401():
    import requests
    response = requests.get(GATEWAY + "/api/v1/migration/status", headers={"Authorization": "Bearer no-es-valido"}, timeout=10)
    assert response.status_code == 401


def test_mobile_can_read(api, sample_member):
    assert api.get("/api/v1/members/" + sample_member, consumer="mobile").status_code == 200
    assert api.get("/api/v1/members/{0}/beneficiaries".format(sample_member), consumer="mobile").status_code == 200


def test_mobile_cannot_write(api, sample_member):
    response = api.post("/api/v1/members/{0}/retirements".format(sample_member),
                        {"requestId": new_request_id("mob"), "date": "2026-10-05", "reason": "no debe pasar"}, consumer="mobile")
    assert response.status_code == 403


def test_mobile_write_is_forbidden_even_for_unknown_member(api):
    response = api.post("/api/v1/members/0000000001/retirements", {"requestId": new_request_id("mob"), "date": "2026-10-05"}, consumer="mobile")
    assert response.status_code == 403


def test_unknown_route_and_wrong_method(api):
    assert api.get("/api/v1/nope").status_code == 404
    assert api.post("/api/v1/migration/status", {}, consumer="subsidios").status_code == 405


def test_errors_never_leak_internals(api):
    for response in (api.get("/api/v1/members/abc"), api.get("/api/v1/nope"),
                     api.post("/api/v1/members/1/retirements", {"requestId": "x", "date": "mal"})):
        body = response.json()
        assert set(body) >= {"message", "error_id"}
        assert "Traceback" not in response.text and "psycopg" not in response.text and "SELECT" not in response.text
