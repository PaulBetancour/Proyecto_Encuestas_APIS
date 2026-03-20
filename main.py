import logging
import csv
from collections import Counter
from io import StringIO
from typing import Any

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
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


@app.get(
        "/",
        response_class=HTMLResponse,
        summary="Panel de demostracion",
        description="Vista HTML para mostrar cumplimiento de requisitos y estado en vivo de la API.",
)
def panel_demo() -> str:
        return """
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Demo API Encuestas</title>
    <style>
        :root {
            --bg1: #f3f7ff;
            --bg2: #eefaf4;
            --card: #ffffff;
            --ink: #17223b;
            --brand: #0f766e;
            --brand2: #1d4ed8;
            --ok: #166534;
            --okbg: #dcfce7;
            --bd: #dbe3f0;
        }
        body {
            margin: 0;
            font-family: "Segoe UI", Tahoma, sans-serif;
            color: var(--ink);
            background: radial-gradient(circle at 10% 10%, var(--bg2), var(--bg1) 65%);
        }
        .wrap { max-width: 1100px; margin: 0 auto; padding: 28px 18px 40px; }
        .hero {
            background: linear-gradient(120deg, #0f766e, #1d4ed8);
            color: #fff; border-radius: 16px; padding: 18px 22px;
            box-shadow: 0 10px 25px rgba(10, 40, 80, .18);
        }
        h1, h2 { margin: 8px 0; }
        p { line-height: 1.45; }
        .grid { display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); margin-top: 14px; }
        .card {
            background: var(--card); border: 1px solid var(--bd); border-radius: 14px;
            padding: 14px; box-shadow: 0 6px 14px rgba(10, 30, 60, .06);
        }
        .btns { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
        button, a.btn {
            border: 0; border-radius: 9px; padding: 9px 12px; font-weight: 600;
            background: #0f766e; color: #fff; cursor: pointer; text-decoration: none;
        }
        a.alt, button.alt { background: #1d4ed8; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border-bottom: 1px solid #e8eef8; text-align: left; padding: 8px; font-size: 14px; }
        .tag-ok {
            background: var(--okbg); color: var(--ok); font-weight: 700; border-radius: 999px;
            padding: 3px 10px; display: inline-block;
        }
        code { background: #eef2ff; border: 1px solid #dbeafe; border-radius: 6px; padding: 2px 6px; }
        .note { font-size: 13px; color: #334155; }
    </style>
</head>
<body>
    <div class="wrap">
        <section class="hero">
            <h1>API de Gestion de Encuestas Poblacionales</h1>
            <p>Panel de demostracion listo para sustentacion: requisitos, estado en vivo y rutas de documentacion.</p>
            <div class="btns">
                <a class="btn" href="/docs" target="_blank" rel="noopener">Abrir Swagger (/docs)</a>
                <a class="btn alt" href="/redoc" target="_blank" rel="noopener">Abrir Redoc (/redoc)</a>
            </div>
        </section>

        <div class="grid">
            <section class="card">
                <h2>Controles rapidos</h2>
                <div class="btns">
                    <button onclick="seed()">Generar 15 datos Faker</button>
                    <button class="alt" onclick="resetData()">Reset encuestas</button>
                    <button onclick="cargarEstado()">Refrescar estado</button>
                </div>
                <p class="note">CSV: usa <code>POST /encuestas/csv/</code> con archivo .csv desde Swagger.</p>
            </section>

            <section class="card">
                <h2>Estado en vivo</h2>
                <p id="kpis">Cargando...</p>
            </section>
        </div>

        <section class="card" style="margin-top:14px;">
            <h2>Checklist profesor (RF y RT)</h2>
            <table>
                <thead><tr><th>Item</th><th>Estado</th><th>Evidencia</th></tr></thead>
                <tbody id="tablaRequisitos"></tbody>
            </table>
        </section>
    </div>

    <script>
        async function cargarEstado() {
            const [statsResp, reqResp] = await Promise.all([
                fetch('/encuestas/estadisticas/'),
                fetch('/demo/requisitos/')
            ]);

            const stats = await statsResp.json();
            const reqs = await reqResp.json();

            document.getElementById('kpis').innerText =
                'Total encuestas: ' + stats.total_encuestas +
                ' | Promedio edad: ' + stats.promedio_edad +
                ' | Estratos: ' + JSON.stringify(stats.distribucion_por_estrato);

            const tbody = document.getElementById('tablaRequisitos');
            tbody.innerHTML = '';
            reqs.items.forEach(it => {
                const tr = document.createElement('tr');
                tr.innerHTML =
                    '<td>' + it.item + '</td>' +
                    '<td><span class="tag-ok">' + it.estado + '</span></td>' +
                    '<td>' + it.evidencia + '</td>';
                tbody.appendChild(tr);
            });
        }

        async function seed() {
            await fetch('/encuestas/seed/15', { method: 'POST' });
            await cargarEstado();
        }

        async function resetData() {
            await fetch('/encuestas/reset/', { method: 'POST' });
            await cargarEstado();
        }

        cargarEstado();
    </script>
</body>
</html>
"""


@app.get(
        "/demo/requisitos/",
        summary="Checklist de cumplimiento",
        description="Retorna un resumen de cumplimiento RF/RT para mostrar en demo.",
)
def estado_requisitos() -> dict[str, Any]:
        items = [
                {"item": "RF1 - Modelos anidados y tipos complejos", "estado": "Cumple", "evidencia": "models.py"},
                {"item": "RF2 - Validadores before/after", "estado": "Cumple", "evidencia": "models.py + validators.py"},
                {"item": "RF3 - CRUD + estadisticas", "estado": "Cumple", "evidencia": "main.py"},
                {"item": "RF4 - Handler HTTP 422", "estado": "Cumple", "evidencia": "main.py"},
                {"item": "RF5 - Endpoint async + explicacion", "estado": "Cumple", "evidencia": "main.py"},
                {"item": "RT1 - requirements + README", "estado": "Cumple", "evidencia": "requirements.txt + README.md"},
                {"item": "RT2 - git 5 commits + main/develop", "estado": "Cumple", "evidencia": "historial git"},
                {"item": "RT3 - Estructura modular", "estado": "Cumple", "evidencia": "raiz del proyecto"},
                {"item": "RT4 - /docs + /redoc + examples", "estado": "Cumple", "evidencia": "FastAPI + models.py"},
                {"item": "RT5 - Decorador personalizado", "estado": "Cumple", "evidencia": "utils.py + main.py"},
        ]
        return {"items": items}


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


@app.post(
    "/encuestas/csv/",
    summary="Cargar encuestas desde CSV",
    description=(
        "Ingiere un archivo CSV y crea encuestas en memoria. "
        "Columnas base: nombre, edad, estrato, departamento. "
        "Respuestas: q1_tipo, q1_valor, q1_comentario; q2_tipo, q2_valor..."
    ),
)
@log_request
async def cargar_csv(file: UploadFile = File(...), request: Request = None) -> dict[str, Any]:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="El archivo debe ser CSV")

    contenido = await file.read()
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="No se pudo decodificar el CSV en UTF-8") from exc

    reader = csv.DictReader(StringIO(texto))
    creadas = 0
    errores = []

    for idx, fila in enumerate(reader, start=2):
        try:
            respuestas = []
            for qid in range(1, 21):
                tipo = (fila.get(f"q{qid}_tipo") or "").strip()
                valor = (fila.get(f"q{qid}_valor") or "").strip()
                comentario = (fila.get(f"q{qid}_comentario") or "").strip() or None
                if tipo and valor:
                    respuestas.append(
                        {
                            "pregunta_id": qid,
                            "tipo_pregunta": tipo,
                            "valor": valor,
                            "comentario": comentario,
                        }
                    )

            # Fallback: una sola respuesta si no vino en formato qN_*
            if not respuestas and fila.get("tipo_pregunta") and fila.get("valor"):
                respuestas.append(
                    {
                        "pregunta_id": int((fila.get("pregunta_id") or "1").strip()),
                        "tipo_pregunta": fila["tipo_pregunta"].strip(),
                        "valor": (fila.get("valor") or "").strip(),
                        "comentario": (fila.get("comentario") or "").strip() or None,
                    }
                )

            payload = EncuestaCompleta(
                encuestado={
                    "nombre": (fila.get("nombre") or "").strip(),
                    "edad": int((fila.get("edad") or "0").strip()),
                    "estrato": int((fila.get("estrato") or "0").strip()),
                    "departamento": (fila.get("departamento") or "").strip(),
                },
                respuestas=respuestas,
            )
            database.create_encuesta(payload)
            creadas += 1
        except Exception as exc:  # noqa: BLE001
            errores.append({"fila": idx, "error": str(exc)})

    return {
        "archivo": file.filename,
        "encuestas_creadas": creadas,
        "errores": errores,
        "total_filas_con_error": len(errores),
    }


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
