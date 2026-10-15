"""Consultas: contrato canónico, errores y sin filtrar el esquema legacy."""

import re

LEGACY_KEYS = {"nro_doc", "nom1", "nom2", "ape1", "ape2", "est_afi", "cod_emp", "nom_emp", "cod_par", "document_number", "status_code"}


def all_keys(value):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from all_keys(nested)
    elif isinstance(value, list):
        for item in value:
            yield from all_keys(item)


def test_health_is_public_and_reports_legacy(api):
    response = api.get("/health", consumer=None)
    assert response.status_code == 200
    assert response.json() == {"status": "UP", "legacy": "UP"}


def test_member_follows_canonical_contract(api, sample_member):
    response = api.get("/api/v1/members/" + sample_member)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"document", "fullName", "status", "company"}
    assert body["document"] == sample_member
    assert body["status"] in ("ACTIVE", "RETIRED", "SUSPENDED")
    assert set(body["company"]) == {"id", "name"}
    assert body["fullName"] == " ".join(body["fullName"].split())


def test_member_response_hides_legacy_names(api, sample_member):
    body = api.get("/api/v1/members/" + sample_member).json()
    assert not {k.lower() for k in all_keys(body)} & LEGACY_KEYS


def test_member_matches_what_education_sees(api, sample_member):
    from conftest import EDUCACION
    import requests
    legacy_view = requests.get("{0}/afiliados/{1}".format(EDUCACION, sample_member), timeout=10).json()
    gateway_view = api.get("/api/v1/members/" + sample_member).json()
    assert gateway_view["fullName"] == legacy_view["nombre"]
    assert gateway_view["company"]["name"] == legacy_view["empresa"]
    assert {"ACTIVE": "ACTIVO", "RETIRED": "RETIRADO", "SUSPENDED": "SUSPENDIDO"}[gateway_view["status"]] == legacy_view["estado"]


def test_unknown_member_returns_404_with_error_format(api):
    response = api.get("/api/v1/members/0000000001")
    assert response.status_code == 404
    body = response.json()
    assert body["message"] and body["error_id"]
    assert not re.search(r"Traceback|Exception|SELECT|psycopg|afi_mae|nro_doc", response.text, re.I)


def test_non_numeric_document_is_not_found_and_not_an_injection(api):
    response = api.get("/api/v1/members/1%27%20OR%20%271%27=%271")
    assert response.status_code == 404
    assert "error_id" in response.json()


def test_beneficiaries_have_canonical_shape(api, sample_member):
    response = api.get("/api/v1/members/{0}/beneficiaries".format(sample_member))
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list) and items
    for item in items:
        assert set(item) == {"document", "fullName", "relationship"}
        assert item["relationship"] in ("SPOUSE", "CHILD", "FATHER", "MOTHER")


def test_beneficiaries_match_legacy_records(api, legacy, sample_member):
    response = api.get("/api/v1/members/{0}/beneficiaries".format(sample_member))
    assert response.status_code == 200

    rows = legacy.query(
        "SELECT nro_doc_ben, nom1, nom2, ape1, ape2, cod_par FROM afi_ben "
        "WHERE nro_doc = %s ORDER BY nro_doc_ben",
        (sample_member,),
    )
    relationships = {"C": "SPOUSE", "H": "CHILD", "P": "FATHER", "M": "MOTHER"}
    expected = [
        {
            "document": row[0],
            "fullName": " ".join(part.strip() for part in row[1:5] if part and part.strip()),
            "relationship": relationships.get(row[5].strip().upper(), "OTHER"),
        }
        for row in rows
    ]
    assert response.json() == expected


def test_beneficiaries_of_unknown_member_is_404(api):
    assert api.get("/api/v1/members/0000000001/beneficiaries").status_code == 404


def test_company_active_members_matches_legacy(api, legacy, sample_member):
    company = api.get("/api/v1/members/" + sample_member).json()["company"]
    response = api.get("/api/v1/companies/" + company["id"])
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"id", "name", "activeMembers"} and body["name"] == company["name"]
    table, _, status = legacy.master()
    expected = legacy.query("SELECT count(*) FROM {0} WHERE cod_emp = %s AND {1} = 'A'".format(table, status), (company["id"],))[0][0]
    assert body["activeMembers"] == expected


def test_unknown_company_is_404(api):
    assert api.get("/api/v1/companies/NOPE").status_code == 404


def test_migration_status_declares_affiliations_state(api):
    body = api.get("/api/v1/migration/status").json()
    assert body["domains"]["affiliations"] in ("LEGACY", "DUAL", "MODERN")
    assert all(v in ("LEGACY", "DUAL", "MODERN") for v in body["domains"].values())
