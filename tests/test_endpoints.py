from fastapi.testclient import TestClient

import database
from main import app


client = TestClient(app)


def _payload_base() -> dict:
    return {
        "encuestado": {
            "nombre": "Laura Jimenez",
            "edad": 29,
            "estrato": 4,
            "departamento": "Valle del Cauca",
        },
        "respuestas": [
            {"pregunta_id": 1, "tipo_pregunta": "likert", "valor": 4, "comentario": "bien"},
            {"pregunta_id": 2, "tipo_pregunta": "porcentaje", "valor": 81.2, "comentario": None},
            {"pregunta_id": 3, "tipo_pregunta": "texto", "valor": "recomendado", "comentario": "rapido"},
        ],
    }


def setup_function() -> None:
    database.reset_db()


def test_post_y_get_encuesta():
    post = client.post("/encuestas/", json=_payload_base())
    assert post.status_code == 201
    eid = post.json()["id"]

    get_one = client.get(f"/encuestas/{eid}")
    assert get_one.status_code == 200
    assert get_one.json()["encuestado"]["nombre"] == "Laura Jimenez"


def test_endpoint_422_estructurado():
    payload = _payload_base()
    payload["encuestado"]["edad"] = 500

    resp = client.post("/encuestas/", json=payload)
    body = resp.json()

    assert resp.status_code == 422
    assert "detalles" in body
    assert body["error"] == "Solicitud invalida (HTTP 422)"


def test_estadisticas_basicas():
    client.post("/encuestas/", json=_payload_base())
    payload2 = _payload_base()
    payload2["encuestado"]["edad"] = 31
    payload2["encuestado"]["estrato"] = 2
    client.post("/encuestas/", json=payload2)

    stats = client.get("/encuestas/estadisticas/")
    assert stats.status_code == 200
    data = stats.json()
    assert data["total_encuestas"] == 2
    assert data["promedio_edad"] == 30.0
    assert data["distribucion_por_estrato"]["2"] == 1


def test_delete_encuesta():
    created = client.post("/encuestas/", json=_payload_base())
    eid = created.json()["id"]

    deleted = client.delete(f"/encuestas/{eid}")
    assert deleted.status_code == 204

    missing = client.get(f"/encuestas/{eid}")
    assert missing.status_code == 404
