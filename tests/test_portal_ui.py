"""Pruebas de regresión de la interfaz web del portal."""

import os

import requests


PORTAL_UI = os.environ.get("PORTAL_UI_BASE_URL", "http://portal-ui:8093").rstrip("/")


def test_portal_homepage_serves_dashboard():
    response = requests.get(PORTAL_UI + "/", timeout=10)

    assert response.status_code == 200
    assert "Portal de servicios | FESC" in response.text
    assert "Encuentra a un afiliado" in response.text
    assert "PORTAL DE SERVICIOS" in response.text
    assert 'aria-controls="resources-panel"' in response.text
    assert "AYUDA Y ESTADO" in response.text
    assert 'class="account-switch"' not in response.text
    assert 'href="#company-card"' in response.text
    assert 'id="language-toggle"' in response.text
    assert 'id="language-panel"' in response.text
    assert 'data-language="es"' in response.text
    assert 'data-language="en"' in response.text


def test_portal_serves_local_assets():
    stylesheet = requests.get(PORTAL_UI + "/assets/styles.css", timeout=10)
    script = requests.get(PORTAL_UI + "/assets/app.js", timeout=10)

    assert stylesheet.status_code == 200
    assert "FESC Orbit" in stylesheet.text
    assert script.status_code == 200
    assert "document.addEventListener('keydown'" in script.text
    assert "resourcesToggle.addEventListener('click'" in script.text
    assert "function maskDocument(value)" in script.text
    assert "function applyLanguage(language)" in script.text
    assert "'fesc-language'" in script.text
    assert 'id="toggle-document"' in requests.get(PORTAL_UI + "/", timeout=10).text


def test_portal_health_reports_gateway_status():
    response = requests.get(PORTAL_UI + "/api/health", timeout=10)

    assert response.status_code == 200
    assert response.json()["status"] == "UP"


def test_portal_member_lookup_returns_canonical_profile():
    response = requests.get(PORTAL_UI + "/api/member/1019886173", timeout=10)

    assert response.status_code == 200
    payload = response.json()
    assert payload["member"]["document"] == "1019886173"
    assert payload["member"]["status"] == "ACTIVE"
    assert payload["company"]["id"] == "2015"
    assert isinstance(payload["beneficiaries"], list)


def test_portal_missing_member_keeps_gateway_error():
    response = requests.get(PORTAL_UI + "/api/member/99999999999999999999", timeout=10)

    assert response.status_code == 404
    assert "message" in response.json()


def test_portal_rejects_unknown_routes():
    response = requests.get(PORTAL_UI + "/unknown", timeout=10)

    assert response.status_code == 404
    assert response.json() == {"message": "ruta no encontrada"}