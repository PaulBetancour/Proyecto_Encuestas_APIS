from pydantic import ValidationError
import pytest

from models import Encuestado, EncuestaCompleta, RespuestaEncuesta


def test_encuestado_departamento_valido():
    enc = Encuestado(nombre="ana perez", edad=30, estrato=2, departamento="  antioquia  ")
    assert enc.departamento == "Antioquia"


def test_encuestado_departamento_invalido():
    with pytest.raises(ValidationError):
        Encuestado(nombre="Ana Perez", edad=30, estrato=2, departamento="Narnia")


def test_respuesta_likert_rango():
    resp = RespuestaEncuesta(pregunta_id=1, tipo_pregunta="likert", valor="5")
    assert resp.valor == 5


def test_respuesta_likert_fuera_rango():
    with pytest.raises(ValidationError):
        RespuestaEncuesta(pregunta_id=1, tipo_pregunta="likert", valor=7)


def test_encuesta_no_permite_preguntas_duplicadas():
    payload = {
        "encuestado": {
            "nombre": "Carlos Lopez",
            "edad": 40,
            "estrato": 3,
            "departamento": "Bogota",
        },
        "respuestas": [
            {"pregunta_id": 1, "tipo_pregunta": "texto", "valor": "ok"},
            {"pregunta_id": 1, "tipo_pregunta": "porcentaje", "valor": 50},
        ],
    }

    with pytest.raises(ValidationError):
        EncuestaCompleta.model_validate(payload)
