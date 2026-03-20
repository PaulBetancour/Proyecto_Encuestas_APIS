# API de Gestion de Encuestas Poblacionales

Proyecto aplicado para la actividad evaluativa del curso: FastAPI + Pydantic + validacion de datos estadisticos.

## 1) Objetivo
Construir una API REST que reciba, valide y almacene en memoria encuestas poblacionales con:
- Tipos complejos y modelos anidados.
- Validadores de campo (`before` y `after`).
- Manejo robusto de errores HTTP 422.
- CRUD completo y endpoint de estadisticas.

## 2) Estructura

```text
.
|-- main.py
|-- models.py
|-- validators.py
|-- database.py
|-- utils.py
|-- requirements.txt
|-- README.md
|-- .gitignore
`-- tests/
    |-- test_models.py
    `-- test_endpoints.py
```

## 3) Entorno virtual (RT1)
Se usa `venv` por ser nativo de Python, liviano y suficiente para este proyecto.

```bash
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 4) Ejecutar API

```bash
uvicorn main:app --reload
```

Documentacion interactiva:
- Swagger UI: http://127.0.0.1:8000/docs
- Redoc: http://127.0.0.1:8000/redoc
- Panel de demostracion (HTML): http://127.0.0.1:8000/

## 5) Endpoints requeridos (RF3)
- `POST /encuestas/` -> registra encuesta (201)
- `GET /encuestas/` -> lista encuestas (200)
- `GET /encuestas/{id}` -> obtiene encuesta por ID (200/404)
- `PUT /encuestas/{id}` -> actualiza encuesta (200/404)
- `DELETE /encuestas/{id}` -> elimina encuesta (204/404)
- `GET /encuestas/estadisticas/` -> resumen estadistico (200)

Extra util para demo:
- `POST /encuestas/seed/{cantidad}` -> genera datos con Faker
- `POST /encuestas/csv/` -> carga un archivo CSV y crea encuestas en memoria

## 6) Cargar CSV para demo

Sube el archivo desde Swagger (`/docs`) usando `POST /encuestas/csv/`.

Formato recomendado por fila:
- `nombre,edad,estrato,departamento`
- Respuestas por pregunta: `q1_tipo,q1_valor,q1_comentario`, `q2_tipo,q2_valor,q2_comentario`, etc.

Ejemplo de cabecera:

```csv
nombre,edad,estrato,departamento,q1_tipo,q1_valor,q1_comentario,q2_tipo,q2_valor,q2_comentario,q3_tipo,q3_valor,q3_comentario
Ana Perez,28,3,Antioquia,likert,5,Excelente,porcentaje,92.4,,texto,Servicio agil,Sin observaciones
```

## 7) Ejemplo de payload

```json
{
  "encuestado": {
    "nombre": "Paul Betancour",
    "edad": 25,
    "estrato": 3,
    "departamento": "Antioquia"
  },
  "respuestas": [
    {"pregunta_id": 1, "tipo_pregunta": "likert", "valor": 5, "comentario": "Excelente"},
    {"pregunta_id": 2, "tipo_pregunta": "porcentaje", "valor": 87.5, "comentario": null},
    {"pregunta_id": 3, "tipo_pregunta": "texto", "valor": "Buen servicio", "comentario": "rapido"}
  ]
}
```

## 8) Pruebas (bonus)

```bash
pytest -q
```

## 9) Requisitos de Git (RT2)
Sugerencia de flujo para entrega:
1. `main` + rama `develop`.
2. Minimo 5 commits significativos.
3. Merge final de `develop` a `main`.

Secuencia recomendada de commits:
1. Estructura base y dependencias.
2. Modelos Pydantic y validadores.
3. Endpoints CRUD + estadisticas.
4. Handler 422 + decorador + Faker seed.
5. Tests y README final.

## 10) Sustentacion (guia rapida)
Preparar explicacion corta de:
- Por que usar modelos anidados.
- Diferencia `mode='before'` vs `mode='after'`.
- Diferencia HTTP 400 vs 422.
- Por que usar `async def` en FastAPI (ASGI).
- Como el decorador agrega logging/tiempos a endpoints.
