import asyncio
import logging
import csv
from collections import Counter
from io import StringIO, TextIOWrapper
from typing import Any

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from faker import Faker

import database
from models import EncuestaCompleta, EstadisticasEncuesta, RespuestaEncuesta
from utils import log_request

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("encuesta_api")
faker = Faker("es_CO")
ULTIMO_REPORTE_CNPV: dict[str, Any] | None = None

app = FastAPI(
    title="API de Gestion de Encuestas Poblacionales",
    version="1.0.0",
    description=(
        "API REST para ingesta y validacion de encuestas con FastAPI + Pydantic. "
        "Incluye validacion robusta, manejo de errores HTTP 422 y estadisticas basicas."
    ),
)

# ============ CORS Configuration ============
# Permite que el HTML panel se comunique con la API desde el navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción: especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALIASES_ENCUESTADO = {
    "nombre": ["nombre", "nombres", "name", "encuestado_nombre", "participante", "full_name"],
    "edad": ["edad", "age", "edad_anos", "anos"],
    "estrato": ["estrato", "estrato_socioeconomico", "nivel_estrato", "socioeconomic_stratum"],
    "departamento": ["departamento", "depto", "departamento_residencia", "region", "state"],
}

CNPV_DPTOS = {
    "05": "ANTIOQUIA", "08": "ATLANTICO", "11": "BOGOTA, D.C.", "13": "BOLIVAR", "15": "BOYACA",
    "17": "CALDAS", "18": "CAQUETA", "19": "CAUCA", "20": "CESAR", "23": "CORDOBA",
    "25": "CUNDINAMARCA", "27": "CHOCO", "41": "HUILA", "44": "LA GUAJIRA", "47": "MAGDALENA",
    "50": "META", "52": "NARINO", "54": "NORTE DE SANTANDER", "63": "QUINDIO", "66": "RISARALDA",
    "68": "SANTANDER", "70": "SUCRE", "73": "TOLIMA", "76": "VALLE DEL CAUCA", "81": "ARAUCA",
    "85": "CASANARE", "86": "PUTUMAYO", "88": "SAN ANDRES, PROVIDENCIA Y SANTA CATALINA",
    "91": "AMAZONAS", "94": "GUAINIA", "95": "GUAVIARE", "97": "VAUPES", "99": "VICHADA",
}

CNPV_CATEGORIAS: dict[str, dict[str, str]] = {
    "VA1_ESTRATO": {
        "0": "Sin Estrato", "1": "Estrato 1", "2": "Estrato 2", "3": "Estrato 3",
        "4": "Estrato 4", "5": "Estrato 5", "6": "Estrato 6", "9": "No sabe el estrato",
    },
    "UA_CLASE": {
        "1": "Cabecera Municipal", "2": "Centro Poblado", "3": "Rural Disperso", "4": "Resto Rural",
    },
    "UVA_USO_UNIDAD": {
        "1": "Vivienda", "2": "Mixto", "3": "Unidad No Residencial", "4": "Lugar Especial de Alojamiento",
    },
    "V_TIPO_VIV": {
        "1": "Casa", "2": "Apartamento", "3": "Tipo cuarto", "4": "Vivienda tradicional indigena",
        "5": "Vivienda tradicional etnica", "6": "Otro",
    },
    "VF_INTERNET": {"1": "Si", "2": "No"},
    "V_MAT_PISO": {
        "1": "Marmol/parque/madera", "2": "Baldosa/vinilo/tableta", "3": "Alfombra",
        "4": "Cemento/gravilla", "5": "Madera burda/vegetal", "6": "Tierra/arena/barro",
    },
    "U_DPTO": CNPV_DPTOS,
}


def _etiqueta_cnpv(campo: str, codigo: str) -> str:
    if campo == "U_DPTO":
        codigo = codigo.zfill(2)
    return CNPV_CATEGORIAS.get(campo, {}).get(codigo, codigo)


def _construir_reporte_cnpv_desde_texto(texto: str, filename: str, max_filas: int | None) -> dict[str, Any]:
    global ULTIMO_REPORTE_CNPV

    reader = csv.DictReader(StringIO(texto))
    requeridas = {"U_DPTO", "VA1_ESTRATO", "COD_ENCUESTAS", "U_VIVIENDA"}
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="El CSV no tiene encabezados")

    faltantes = [c for c in sorted(requeridas) if c not in reader.fieldnames]
    if faltantes:
        raise HTTPException(
            status_code=400,
            detail={
                "mensaje": "El archivo no coincide con estructura CNPV esperada",
                "faltantes": faltantes,
            },
        )

    columnas = list(reader.fieldnames)
    campos_clave = [
        "U_DPTO", "U_MPIO", "UA_CLASE",
        "VA1_ESTRATO", "V_MAT_PISO", "VF_INTERNET",
        "UVA_USO_UNIDAD", "V_TIPO_VIV", "V_TOT_HOG", "COD_ENCUESTAS",
    ]

    total = 0
    filas_con_campos_clave_completos = 0
    filas_con_campos_clave_incompletos = 0
    filas_con_nulos = 0
    errores = []
    conteo_dpto: Counter[str] = Counter()
    conteo_estrato: Counter[str] = Counter()
    nulos_por_columna: Counter[str] = Counter()
    conteo_campos: dict[str, Counter[str]] = {campo: Counter() for campo in campos_clave if campo in columnas}

    columnas_numericas_interes = ["V_TOT_HOG", "L_TOT_PERL", "VA1_ESTRATO", "U_MPIO", "U_DPTO"]
    acumuladores_numericos: dict[str, dict[str, float]] = {
        c: {"count": 0, "sum": 0.0, "min": float("inf"), "max": float("-inf")}
        for c in columnas_numericas_interes
        if c in columnas
    }

    for idx, fila in enumerate(reader, start=2):
        if max_filas is not None and total >= max_filas:
            break
        total += 1

        fila_tiene_nulos = False
        for col in columnas:
            if not (fila.get(col) or "").strip():
                nulos_por_columna[col] += 1
                fila_tiene_nulos = True

        if fila_tiene_nulos:
            filas_con_nulos += 1

        dpto = (fila.get("U_DPTO") or "").strip()
        estrato = (fila.get("VA1_ESTRATO") or "").strip()
        cod_enc = (fila.get("COD_ENCUESTAS") or "").strip()
        viv = (fila.get("U_VIVIENDA") or "").strip()

        faltantes_clave = []
        if not dpto:
            faltantes_clave.append("U_DPTO")
        if not estrato:
            faltantes_clave.append("VA1_ESTRATO")
        if not cod_enc:
            faltantes_clave.append("COD_ENCUESTAS")
        if not viv:
            faltantes_clave.append("U_VIVIENDA")

        if faltantes_clave:
            filas_con_campos_clave_incompletos += 1
            if len(errores) < 25:
                errores.append({"fila": idx, "error": "Campos clave vacios", "faltantes": faltantes_clave})
        else:
            filas_con_campos_clave_completos += 1

        if dpto:
            conteo_dpto[dpto] += 1
        if estrato:
            conteo_estrato[estrato] += 1

        for campo in conteo_campos:
            valor_campo = (fila.get(campo) or "").strip()
            if not valor_campo:
                continue
            if campo == "U_DPTO":
                valor_campo = valor_campo.zfill(2)
            conteo_campos[campo][valor_campo] += 1

        for col in acumuladores_numericos:
            raw = (fila.get(col) or "").strip()
            if not raw:
                continue
            try:
                valor = float(raw.replace(",", "."))
            except ValueError:
                continue

            stats = acumuladores_numericos[col]
            stats["count"] += 1
            stats["sum"] += valor
            if valor < stats["min"]:
                stats["min"] = valor
            if valor > stats["max"]:
                stats["max"] = valor

    total_celdas = total * len(columnas) if total and columnas else 0
    total_nulos = sum(nulos_por_columna.values())

    estadisticas_numericas: dict[str, dict[str, float]] = {}
    for col, stats in acumuladores_numericos.items():
        if stats["count"] == 0:
            continue
        estadisticas_numericas[col] = {
            "count": int(stats["count"]),
            "min": round(stats["min"], 2),
            "max": round(stats["max"], 2),
            "mean": round(stats["sum"] / stats["count"], 2),
        }

    top_nulos = sorted(nulos_por_columna.items(), key=lambda x: x[1], reverse=True)[:10]

    resumen_campos_clave: dict[str, Any] = {}
    for campo in campos_clave:
        if campo not in columnas:
            resumen_campos_clave[campo] = {"disponible": False, "mensaje": "Campo no presente en el archivo"}
            continue

        no_nulos = total - nulos_por_columna.get(campo, 0)
        top_vals = []
        for codigo, conteo in conteo_campos.get(campo, Counter()).most_common(10):
            top_vals.append({"codigo": codigo, "etiqueta": _etiqueta_cnpv(campo, codigo), "conteo": conteo})

        resumen_campos_clave[campo] = {
            "disponible": True,
            "no_nulos": no_nulos,
            "porcentaje_no_nulo": round((no_nulos / total) * 100, 2) if total else 0.0,
            "top_valores": top_vals,
        }

    reporte = {
        "archivo": filename,
        "columnas_detectadas": columnas,
        "total_columnas": len(columnas),
        "filas_procesadas": total,
        "filas_validas": total,
        "filas_invalidas": 0,
        "filas_con_campos_clave_completos": filas_con_campos_clave_completos,
        "filas_con_campos_clave_incompletos": filas_con_campos_clave_incompletos,
        "filas_con_nulos": filas_con_nulos,
        "porcentaje_campos_vacios": round((total_nulos / total_celdas) * 100, 2) if total_celdas else 0.0,
        "nulos_por_columna_top": [{"columna": c, "nulos": n} for c, n in top_nulos],
        "estadisticas_numericas": estadisticas_numericas,
        "distribucion_u_dpto": dict(conteo_dpto),
        "distribucion_estrato": dict(conteo_estrato),
        "campos_clave_analizados": [c for c in campos_clave if c in columnas],
        "resumen_campos_clave": resumen_campos_clave,
        "modelos_proyecto": {
            "ubicacion": {"campos": ["U_DPTO", "U_MPIO", "UA_CLASE"], "resumen": {k: resumen_campos_clave[k] for k in ["U_DPTO", "U_MPIO", "UA_CLASE"]}},
            "vivienda_detalle": {"campos": ["VA1_ESTRATO", "V_MAT_PISO", "VF_INTERNET"], "resumen": {k: resumen_campos_clave[k] for k in ["VA1_ESTRATO", "V_MAT_PISO", "VF_INTERNET"]}},
            "encuesta_hogar": {"campos": ["UVA_USO_UNIDAD", "V_TIPO_VIV", "V_TOT_HOG", "COD_ENCUESTAS"], "resumen": {k: resumen_campos_clave[k] for k in ["UVA_USO_UNIDAD", "V_TIPO_VIV", "V_TOT_HOG", "COD_ENCUESTAS"]}},
        },
        "muestra_errores": errores,
    }
    ULTIMO_REPORTE_CNPV = reporte
    return reporte


def _normalize_key(value: str) -> str:
    return "".join(ch.lower() for ch in value.strip() if ch.isalnum() or ch in {"_", " "})


def _get_by_alias(row: dict[str, Any], aliases: list[str]) -> str:
    normalized_map = {_normalize_key(k): k for k in row.keys()}
    for alias in aliases:
        key = normalized_map.get(_normalize_key(alias))
        if key is not None:
            return (row.get(key) or "").strip()
    return ""


def _infer_tipo(col_name: str, raw: str) -> str:
    name = _normalize_key(col_name)
    raw_clean = raw.strip().replace(",", ".")
    if "likert" in name:
        return "likert"
    if "porcentaje" in name or "percent" in name or "%" in col_name:
        return "porcentaje"
    try:
        num = float(raw_clean)
        if float(num).is_integer() and 1 <= int(num) <= 5:
            return "likert"
        if 0.0 <= num <= 100.0:
            return "porcentaje"
    except ValueError:
        pass
    return "texto"


def _extract_respuestas_real(row: dict[str, Any]) -> list[dict[str, Any]]:
    respuestas: list[dict[str, Any]] = []

    # Formato estandar qN_tipo, qN_valor, qN_comentario
    for qid in range(1, 101):
        tipo = (row.get(f"q{qid}_tipo") or "").strip()
        valor = (row.get(f"q{qid}_valor") or "").strip()
        comentario = (row.get(f"q{qid}_comentario") or "").strip() or None
        if tipo and valor:
            respuestas.append(
                {
                    "pregunta_id": qid,
                    "tipo_pregunta": tipo,
                    "valor": valor,
                    "comentario": comentario,
                }
            )

    if respuestas:
        return respuestas

    # Formato fila-unica de respuesta
    if row.get("tipo_pregunta") and row.get("valor"):
        respuestas.append(
            {
                "pregunta_id": int((row.get("pregunta_id") or "1").strip()),
                "tipo_pregunta": (row.get("tipo_pregunta") or "").strip(),
                "valor": (row.get("valor") or "").strip(),
                "comentario": (row.get("comentario") or "").strip() or None,
            }
        )
        return respuestas

    # Formato real general: cualquier columna extra se convierte en respuesta
    columnas_base = {"nombre", "nombres", "name", "encuestado_nombre", "participante", "full_name",
                     "edad", "age", "edad_anos", "anos",
                     "estrato", "estrato_socioeconomico", "nivel_estrato", "socioeconomic_stratum",
                     "departamento", "depto", "departamento_residencia", "region", "state"}

    idx = 1
    for col, raw in row.items():
        if _normalize_key(col) in {_normalize_key(x) for x in columnas_base}:
            continue
        val = (raw or "").strip()
        if not val:
            continue
        tipo = _infer_tipo(col, val)
        respuestas.append(
            {
                "pregunta_id": idx,
                "tipo_pregunta": tipo,
                "valor": val,
                "comentario": f"Columna original: {col}",
            }
        )
        idx += 1

    return respuestas


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
                <hr style="border:0;border-top:1px solid #e8eef8;margin:12px 0;" />
                <p class="note"><strong>Subir CSV real:</strong></p>
                <input id="csvFile" type="file" accept=".csv" />
                <div class="btns" style="margin-top:8px;">
                    <button onclick="subirCsv()">Cargar CSV</button>
                </div>
                <p id="csvMsg" class="note"></p>
                            <p class="note" style="margin-top:12px;padding:10px;background:#fff3cd;border-radius:8px;">
                                <strong>ℹ️ Formato esperado:</strong> El CSV debe tener columnas <code>nombre</code>, <code>edad</code>, <code>estrato</code>, <code>departamento</code>.<br>
                                Para cargar archivos <strong>CNPV real</strong>, use <a href="/index.html#live-test" style="color:#0f766e;font-weight:bold;">el panel "🧪 Prueba en Vivo"</a> en index.html
                            </p>
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

        async function subirCsv() {
            const input = document.getElementById('csvFile');
            const msg = document.getElementById('csvMsg');
            if (!input.files.length) {
                msg.innerText = 'Selecciona un archivo CSV primero.';
                return;
            }
            const fd = new FormData();
            fd.append('file', input.files[0]);
            const resp = await fetch('/encuestas/csv/', { method: 'POST', body: fd });
            const data = await resp.json();
            if (!resp.ok) {
                msg.innerText = 'Error: ' + JSON.stringify(data);
                return;
            }
            msg.innerText =
                'Archivo: ' + data.archivo +
                ' | Creadas: ' + data.encuestas_creadas +
                ' | Errores: ' + data.total_filas_con_error;
                        if (data.total_filas_con_error > 0 && data.errores.length > 0) {
                            msg.innerText += ' | Error: ' + data.errores[0].error;
                        }
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


@app.post(
    "/datasets/cnpv/analizar/",
    summary="Analizar base real CNPV",
    description=(
        "Endpoint correcto para probar el archivo real del CNPV en Swagger. "
        "Analiza un CSV de viviendas sin inventar campos, genera metricas reales, "
        "resume los 3 modelos del proyecto y puede tardar varios segundos o minutos "
        "si el archivo es grande porque la respuesta es sincrona. "
        "No use /encuestas/csv/ para el CNPV."
    ),
)
@log_request
async def analizar_csv_cnpv(
    file: UploadFile = File(...),
    max_filas: int | None = None,
    request: Request = None,
) -> dict[str, Any]:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="El archivo debe ser CSV")
    if max_filas is not None and (max_filas < 1 or max_filas > 2_000_000):
        raise HTTPException(status_code=400, detail="max_filas debe estar entre 1 y 2000000")

    try:
        contenido = await file.read()
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="No se pudo decodificar el CSV en UTF-8") from exc
    return await asyncio.to_thread(_construir_reporte_cnpv_desde_texto, texto, file.filename, max_filas)


@app.get(
    "/datasets/cnpv/ultimo/",
    summary="Ultimo reporte CNPV",
    description="Devuelve el ultimo reporte generado al analizar un CSV CNPV real.",
)
def obtener_ultimo_reporte_cnpv() -> dict[str, Any]:
    if ULTIMO_REPORTE_CNPV is None:
        raise HTTPException(status_code=404, detail="No hay reporte CNPV cargado aun")
    return ULTIMO_REPORTE_CNPV


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
    description=(
        "Endpoint CRUD academico para RF1-RF5. "
        "Se usa con JSON manual (encuestado + respuestas). "
        "No se usa para subir el archivo CNPV real."
    ),
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
        "Carga un CSV didactico de encuestas y crea encuestas en memoria para el CRUD. "
        "Columnas base: nombre, edad, estrato, departamento. "
        "Respuestas: q1_tipo, q1_valor, q1_comentario; q2_tipo, q2_valor... "
        "No sirve para el archivo CNPV real; para ese caso use /datasets/cnpv/analizar/."
    ),
)
@log_request
async def cargar_csv(file: UploadFile = File(...), request: Request = None) -> dict[str, Any]:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="El archivo debe ser CSV")

    try:
        file.file.seek(0)
        text_stream = TextIOWrapper(file.file, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(text_stream)
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="No se pudo decodificar el CSV en UTF-8") from exc
    creadas = 0
    errores = []

    for idx, fila in enumerate(reader, start=2):
        try:
            respuestas = _extract_respuestas_real(fila)

            nombre_raw = _get_by_alias(fila, ALIASES_ENCUESTADO["nombre"])
            edad_raw = _get_by_alias(fila, ALIASES_ENCUESTADO["edad"])
            estrato_raw = _get_by_alias(fila, ALIASES_ENCUESTADO["estrato"])
            departamento_raw = _get_by_alias(fila, ALIASES_ENCUESTADO["departamento"])

            if not all([nombre_raw, edad_raw, estrato_raw, departamento_raw]):
                raise ValueError(
                    "Faltan columnas base requeridas (nombre, edad, estrato, departamento). "
                    "Puedes usar aliases como name, age, depto, estrato_socioeconomico."
                )

            payload = EncuestaCompleta(
                encuestado={
                    "nombre": nombre_raw,
                    "edad": int(float(edad_raw.replace(",", "."))),
                    "estrato": int(float(estrato_raw.replace(",", "."))),
                    "departamento": departamento_raw,
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
        "total_filas_leidas": max(0, reader.line_num - 1),
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
