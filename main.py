import logging
from collections import Counter
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from faker import Faker

import database
from models import EncuestaCompleta, EstadisticasEncuesta, RespuestaEncuesta
from utils import log_request

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("encuesta_api")
faker = Faker("es_CO")

app = FastAPI(
    title="API de Gestion de Encuestas Poblacionales",
    version="1.0.0",
    description=(
        "API REST para ingesta y validacion de encuestas con FastAPI + Pydantic. "
        "Incluye validacion robusta, manejo de errores HTTP 422 y estadisticas basicas."
    ),
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("Ingesta invalida en %s %s", request.method, request.url.path)

    detalles = []
    for error in exc.errors():
        detalles.append(
            {
                "campo": " -> ".join(str(x) for x in error.get("loc", [])),
                "mensaje": error.get("msg", "Error de validacion"),
                "tipo": error.get("type", "validation_error"),
                "valor": error.get("input"),
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Solicitud invalida (HTTP 422)",
            "mensaje": "Los datos enviados no cumplen el esquema o las reglas de validacion.",
            "detalles": detalles,
        },
    )


@app.post(
    "/encuestas/",
    response_model=EncuestaCompleta,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una encuesta completa",
    description="Registra una encuesta con datos demograficos del encuestado y sus respuestas.",
)
@log_request
def crear_encuesta(encuesta: EncuestaCompleta, request: Request) -> EncuestaCompleta:
    return database.create_encuesta(encuesta)


@app.get(
    "/encuestas/",
    response_model=list[EncuestaCompleta],
    summary="Listar todas las encuestas",
    description="Retorna todas las encuestas almacenadas en memoria.",
)
@log_request
async def listar_encuestas(request: Request) -> list[EncuestaCompleta]:
    # RF5:
    # - def: bloquea el worker mientras espera I/O.
    # - async def: libera el event loop durante operaciones de espera.
    # - FastAPI corre sobre ASGI (no WSGI), por eso soporta concurrencia async/await.
    # Es indispensable cuando hay BD remotas, colas, HTTP externo o archivos en alta concurrencia.
    return database.list_encuestas()


@app.get(
    "/encuestas/estadisticas/",
    response_model=EstadisticasEncuesta,
    summary="Resumen estadistico",
    description="Retorna conteo total, promedio de edad y distribucion por estrato socioeconomico.",
)
@log_request
def obtener_estadisticas(request: Request) -> EstadisticasEncuesta:
    encuestas = database.list_encuestas()
    total = len(encuestas)

    if total == 0:
        return EstadisticasEncuesta(total_encuestas=0, promedio_edad=0.0, distribucion_por_estrato={})

    edades = [e.encuestado.edad for e in encuestas]
    conteo_estrato = Counter(e.encuestado.estrato for e in encuestas)

    return EstadisticasEncuesta(
        total_encuestas=total,
        promedio_edad=round(sum(edades) / total, 2),
        distribucion_por_estrato=dict(sorted(conteo_estrato.items())),
    )


@app.get(
    "/encuestas/{encuesta_id}",
    response_model=EncuestaCompleta,
    summary="Obtener encuesta por ID",
    description="Busca una encuesta por su identificador. Retorna 404 si no existe.",
)
@log_request
def obtener_encuesta_por_id(encuesta_id: int, request: Request) -> EncuestaCompleta:
    encuesta = database.get_encuesta(encuesta_id)
    if encuesta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encuesta no encontrada")
    return encuesta


@app.put(
    "/encuestas/{encuesta_id}",
    response_model=EncuestaCompleta,
    summary="Actualizar encuesta existente",
    description="Reemplaza una encuesta existente por su ID. Retorna 404 si no existe.",
)
@log_request
def actualizar_encuesta(encuesta_id: int, encuesta: EncuestaCompleta, request: Request) -> EncuestaCompleta:
    actualizada = database.update_encuesta(encuesta_id, encuesta)
    if actualizada is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encuesta no encontrada")
    return actualizada


@app.delete(
    "/encuestas/{encuesta_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    summary="Eliminar encuesta",
    description="Elimina una encuesta por su ID. Retorna 404 si no existe.",
)
@log_request
def eliminar_encuesta(encuesta_id: int, request: Request) -> None:
    eliminado = database.delete_encuesta(encuesta_id)
    if not eliminado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encuesta no encontrada")
    return None


@app.post(
    "/encuestas/seed/{cantidad}",
    summary="Generar encuestas de prueba con Faker",
    description="Genera encuestas sinteticas para pruebas locales y demostracion.",
)
@log_request
def generar_datos_prueba(cantidad: int, request: Request) -> dict[str, Any]:
    if cantidad < 1 or cantidad > 200:
        raise HTTPException(status_code=400, detail="cantidad debe estar entre 1 y 200")

    tipos = ["likert", "porcentaje", "texto"]

    for _ in range(cantidad):
        respuestas = []
        for pid in range(1, 4):
            tipo = tipos[pid - 1]
            if tipo == "likert":
                valor = faker.random_int(min=1, max=5)
            elif tipo == "porcentaje":
                valor = round(faker.pyfloat(min_value=0, max_value=100, right_digits=2), 2)
            else:
                valor = faker.sentence(nb_words=6)

            respuestas.append(
                RespuestaEncuesta(
                    pregunta_id=pid,
                    tipo_pregunta=tipo,
                    valor=valor,
                    comentario=faker.sentence(nb_words=4) if faker.boolean(chance_of_getting_true=35) else None,
                )
            )

        payload = EncuestaCompleta(
            encuestado={
                "nombre": faker.name(),
                "edad": faker.random_int(min=18, max=85),
                "estrato": faker.random_int(min=1, max=6),
                "departamento": faker.random_element(
                    elements=[
                        "Antioquia",
                        "Bogota",
                        "Valle del Cauca",
                        "Atlantico",
                        "Cundinamarca",
                        "Santander",
                    ]
                ),
            },
            respuestas=respuestas,
        )
        database.create_encuesta(payload)

    return {"mensaje": "Datos de prueba generados", "cantidad": cantidad}


@app.post("/encuestas/reset/", include_in_schema=False)
def reset_encuestas() -> dict[str, str]:
    database.reset_db()
    return {"status": "ok"}
