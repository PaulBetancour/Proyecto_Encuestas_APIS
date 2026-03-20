#!/usr/bin/env python3
"""
cliente_api.py — Cliente Python consumidor de la API de Encuestas USTA
======================================================================
Detecta automáticamente el tipo de CSV (CNPV o encuestas_demo),
sube el archivo a la API y genera un reporte estadístico con pandas.

Uso:
    python cliente_api.py <ruta_al_csv> [max_filas]

Ejemplos:
    python cliente_api.py data/entrada/encuestas_demo.csv
    python cliente_api.py data/entrada/CNPV2018_1VIV_A2_11.CSV 5000
    python cliente_api.py plantilla_encuestas.csv
"""

import csv
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path

import httpx
import pandas as pd

# ──────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────
API_BASE = "http://127.0.0.1:8000"
TIMEOUT_SEGUNDOS = 120

# Columnas mínimas para identificar cada tipo de CSV
CNPV_COLS = {"U_DPTO", "VA1_ESTRATO", "COD_ENCUESTAS", "U_VIVIENDA"}
ENCUESTAS_COLS = {"nombre", "edad", "estrato", "departamento"}


# ──────────────────────────────────────────────
# Detección de tipo de CSV
# ──────────────────────────────────────────────
def detect_csv_type(csv_path: Path) -> str:
    """
    Lee solo la primera línea del CSV para identificar su tipo.
    Retorna: 'cnpv' | 'encuestas' | 'desconocido'
    """
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        first_line = f.readline()

    headers = {h.strip().strip('"') for h in first_line.split(",")}
    headers_upper = {h.upper() for h in headers}

    if CNPV_COLS.issubset(headers_upper):
        return "cnpv"
    if ENCUESTAS_COLS.issubset(headers):
        return "encuestas"
    return "desconocido"


# ──────────────────────────────────────────────
# Llamadas a la API
# ──────────────────────────────────────────────
def upload_cnpv(csv_path: Path, max_filas: int = 5000) -> dict:
    """POST /datasets/cnpv/analizar/ — analiza archivo CNPV real."""
    with open(csv_path, "rb") as f:
        response = httpx.post(
            f"{API_BASE}/datasets/cnpv/analizar/",
            params={"max_filas": max_filas},
            files={"file": (csv_path.name, f, "text/csv")},
            timeout=TIMEOUT_SEGUNDOS,
        )
    response.raise_for_status()
    return response.json()


def upload_encuestas(csv_path: Path) -> dict:
    """POST /encuestas/csv/ — importa encuestas en memoria."""
    with open(csv_path, "rb") as f:
        response = httpx.post(
            f"{API_BASE}/encuestas/csv/",
            files={"file": (csv_path.name, f, "text/csv")},
            timeout=TIMEOUT_SEGUNDOS,
        )
    response.raise_for_status()
    return response.json()


def get_encuestas() -> list[dict]:
    """GET /encuestas/ — obtiene todas las encuestas cargadas en memoria."""
    response = httpx.get(f"{API_BASE}/encuestas/", timeout=30)
    response.raise_for_status()
    data = response.json()
    # La API puede devolver lista directa o dict con 'items'
    return data if isinstance(data, list) else data.get("items", [])


# ──────────────────────────────────────────────
# Reportes estadísticos con pandas
# ──────────────────────────────────────────────
def reporte_cnpv(data: dict, csv_path: Path) -> None:
    """Genera y guarda el reporte estadístico de un archivo CNPV."""
    separador = "─" * 60

    print(f"\n{'═'*60}")
    print("  REPORTE ESTADÍSTICO — CNPV")
    print(f"{'═'*60}")
    print(f"  Archivo          : {data['archivo']}")
    print(f"  Filas procesadas : {data['filas_procesadas']:,}")
    print(f"  Filas válidas    : {data['filas_validas']:,}")
    print(f"  Filas con error  : {data['filas_invalidas']:,}")

    # ── Distribución por departamento ──
    df_dpto = (
        pd.DataFrame(
            list(data["distribucion_u_dpto"].items()),
            columns=["Departamento", "Viviendas"],
        )
        .sort_values("Viviendas", ascending=False)
        .reset_index(drop=True)
    )

    print(f"\n{separador}")
    print("  Top 15 Departamentos por cantidad de viviendas")
    print(separador)
    print(df_dpto.head(15).to_string(index=False))

    # ── Distribución por estrato ──
    df_estrato = (
        pd.DataFrame(
            list(data["distribucion_estrato"].items()),
            columns=["Estrato", "Viviendas"],
        )
        .sort_values("Estrato")
        .reset_index(drop=True)
    )

    print(f"\n{separador}")
    print("  Distribución por Estrato Socioeconómico")
    print(separador)
    print(df_estrato.to_string(index=False))

    # ── Estadísticas descriptivas de los conteos ──
    print(f"\n{separador}")
    print("  Estadísticas descriptivas (viviendas por departamento)")
    print(separador)
    stats = df_dpto["Viviendas"].describe()
    stats.index = ["Dptos.", "Promedio", "Desv. Est.", "Mín.", "Q1", "Mediana", "Q3", "Máx."]
    print(stats.to_string())

    # ── Porcentaje de validez ──
    pct = (data["filas_validas"] / data["filas_procesadas"] * 100) if data["filas_procesadas"] else 0
    print(f"\n  Tasa de calidad: {pct:.1f}%")

    # ── Guardar CSV del reporte ──
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = csv_path.parent
    out = out_dir / f"reporte_cnpv_{ts}.csv"
    df_dpto.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n  ✔ Reporte guardado en: {out}")

    if data.get("muestra_errores"):
        print(f"\n{separador}")
        print("  Muestra de errores de validación")
        print(separador)
        for e in data["muestra_errores"][:5]:
            print(f"  Fila {e['fila']}: {e['error']}")


def reporte_encuestas(data: dict, csv_path: Path) -> None:
    """Genera y guarda el reporte estadístico de un archivo de encuestas."""
    separador = "─" * 60

    print(f"\n{'═'*60}")
    print("  REPORTE ESTADÍSTICO — ENCUESTAS")
    print(f"{'═'*60}")
    print(f"  Archivo          : {data['archivo']}")
    print(f"  Encuestas creadas: {data['encuestas_creadas']}")
    print(f"  Filas leídas     : {data['total_filas_leidas']}")
    print(f"  Filas con error  : {data['total_filas_con_error']}")

    # Análisis local del CSV con pandas
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    print(f"\n{separador}")
    print("  Vista general del dataset")
    print(separador)
    print(f"  Filas: {len(df)}  |  Columnas: {len(df.columns)}")
    print(f"  Columnas: {', '.join(df.columns.tolist())}")

    # ── Distribución por estrato ──
    if "estrato" in df.columns:
        print(f"\n{separador}")
        print("  Distribución por Estrato Socioeconómico")
        print(separador)
        estrato_counts = df["estrato"].value_counts().sort_index()
        print(estrato_counts.to_string())

    # ── Distribución por departamento ──
    if "departamento" in df.columns:
        print(f"\n{separador}")
        print("  Distribución por Departamento")
        print(separador)
        print(df["departamento"].value_counts().to_string())

    # ── Estadísticas de la columna edad ──
    if "edad" in df.columns:
        print(f"\n{separador}")
        print("  Estadísticas de Edad")
        print(separador)
        edad_stats = df["edad"].describe()
        edad_stats.index = ["Count", "Promedio", "Desv. Est.", "Mín.", "Q1", "Mediana", "Q3", "Máx."]
        print(edad_stats.to_string())

    # ── Estadísticas de respuestas (columnas _valor) ──
    valor_cols = [c for c in df.columns if c.endswith("_valor")]
    if valor_cols:
        print(f"\n{separador}")
        print("  Estadísticas de Respuestas (valores numéricos)")
        print(separador)
        print(df[valor_cols].describe().to_string())

    # ── Recuperar encuestas de la API para validar ──
    try:
        encuestas = get_encuestas()
        if encuestas:
            print(f"\n{separador}")
            print(f"  Verificación API: {len(encuestas)} encuestas actualmente en memoria")
            print(separador)
            df_api = pd.json_normalize(encuestas)
            enc_cols = [c for c in df_api.columns if "encuestado" in c]
            if enc_cols:
                print(df_api[enc_cols].head(5).to_string(index=False))
    except Exception:
        pass  # No crítico si la API no responde en este paso

    # ── Guardar reporte ──
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = csv_path.parent
    out = out_dir / f"reporte_encuestas_{ts}.csv"
    df.describe(include="all").to_csv(out, encoding="utf-8-sig")
    print(f"\n  ✔ Reporte guardado en: {out}")

    # ── Mostrar errores ──
    if data.get("errores"):
        print(f"\n{separador}")
        print("  Primeros errores de importación")
        print(separador)
        for e in data["errores"][:5]:
            print(f"  Fila {e['fila']}: {e['error']}")


# ──────────────────────────────────────────────
# Punto de entrada
# ──────────────────────────────────────────────
def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"Error: no existe el archivo '{csv_path}'")
        sys.exit(1)

    max_filas = int(sys.argv[2]) if len(sys.argv) > 2 else 5000

    tipo = detect_csv_type(csv_path)

    print(f"Archivo : {csv_path.name}")
    print(f"Tipo    : {tipo}")
    print(f"Servidor: {API_BASE}")

    if tipo == "desconocido":
        print("\nError: CSV no reconocido. Columnas mínimas esperadas:")
        print(f"  CNPV     : {', '.join(sorted(CNPV_COLS))}")
        print(f"  Encuestas: {', '.join(sorted(ENCUESTAS_COLS))}")
        sys.exit(1)

    try:
        if tipo == "cnpv":
            print(f"Subiendo a /datasets/cnpv/analizar/ (max_filas={max_filas})...")
            data = upload_cnpv(csv_path, max_filas)
            reporte_cnpv(data, csv_path)
        else:
            print("Subiendo a /encuestas/csv/...")
            data = upload_encuestas(csv_path)
            reporte_encuestas(data, csv_path)

    except httpx.ConnectError:
        print(f"\nError: No se puede conectar a {API_BASE}")
        print("¿Está corriendo el servidor? Ejecute:")
        print("  uvicorn main:app --host 127.0.0.1 --port 8000 --reload")
        sys.exit(1)

    except httpx.HTTPStatusError as e:
        print(f"\nError HTTP {e.response.status_code}:")
        try:
            detail = e.response.json().get("detail", e.response.text)
            print(f"  {detail}")
        except Exception:
            print(f"  {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
