# Validacion de requisitos - Actividad Evaluativa

## Resumen
Este documento cruza cada requisito de la actividad con la evidencia de implementacion en el proyecto.

## RF1 - Modelos Pydantic con tipos complejos
- Estado: CUMPLE
- Evidencia:
  - `Encuestado`, `RespuestaEncuesta`, `EncuestaCompleta` en `models.py`.
  - Uso de `Union[int, float, str]`, `Optional[str]`, `list[RespuestaEncuesta]`.
  - Estructura anidada: `EncuestaCompleta` contiene `encuestado + respuestas`.

## RF2 - Validadores @field_validator
- Estado: CUMPLE
- Evidencia:
  - `mode='before'`: `limpiar_nombre`, `validar_departamento`, `normalizar_valor_entrada`.
  - `mode='after'`: `validar_estrato_entero`, `validar_valor_por_tipo`.
  - Reglas implementadas:
    - Edad: `Field(ge=0, le=120)`.
    - Estrato: `Field(ge=1, le=6)` + validador.
    - Departamento: contra lista oficial en `validators.py`.
    - Puntajes: Likert 1-5 y porcentaje 0-100 segun `tipo_pregunta`.

## RF3 - Endpoints API REST
- Estado: CUMPLE
- Evidencia en `main.py`:
  - `POST /encuestas/` -> 201
  - `GET /encuestas/` -> 200
  - `GET /encuestas/{encuesta_id}` -> 200/404
  - `PUT /encuestas/{encuesta_id}` -> 200/404
  - `DELETE /encuestas/{encuesta_id}` -> 204/404
  - `GET /encuestas/estadisticas/` -> 200

## RF4 - Manejo de errores HTTP 422
- Estado: CUMPLE
- Evidencia:
  - Handler `@app.exception_handler(RequestValidationError)` en `main.py`.
  - Respuesta JSON estructurada con `campo`, `mensaje`, `tipo`, `valor`.
  - Logging de intentos invalidos con `logger.warning`.

## RF5 - Endpoint asincrono + explicacion
- Estado: CUMPLE
- Evidencia:
  - Endpoint `async def listar_encuestas` en `main.py`.
  - Comentario en codigo sobre:
    - diferencia `def` vs `async def`
    - escenario practico de uso
    - relacion con ASGI

## RT1 - Entorno virtual y dependencias
- Estado: CUMPLE
- Evidencia:
  - `requirements.txt` funcional.
  - Instrucciones de `venv` en `README.md`.

## RT2 - Git y flujo
- Estado: LISTO PARA EJECUTAR EN REPO
- Evidencia:
  - `.gitignore` correcto.
  - Estrategia de ramas y commits propuesta en `README.md`.
- Nota:
  - La creacion de commits/rama se debe ejecutar en tu repositorio remoto.

## RT3 - Estructura del proyecto
- Estado: CUMPLE
- Evidencia:
  - `main.py`, `models.py`, `validators.py`, `requirements.txt`, `README.md`, `.gitignore`, `tests/`.
  - Adicionales utiles: `database.py`, `utils.py`.

## RT4 - Swagger / Redoc
- Estado: CUMPLE
- Evidencia:
  - Endpoints con `summary` y `description`.
  - Modelos con `json_schema_extra` en `models.py`.
  - FastAPI expone `/docs` y `/redoc`.

## RT5 - Decorador personalizado
- Estado: CUMPLE
- Evidencia:
  - Decorador `@log_request` en `utils.py`.
  - Aplicado a endpoints en `main.py`.
  - Comentario conceptual de relacion con decoradores de FastAPI incluido en `utils.py`.

## Bonus aplicado
- +0.1 Tests unitarios:
  - `tests/test_models.py`
  - `tests/test_endpoints.py`
  - Resultado local: 9 pruebas aprobadas.
- Uso de Faker:
  - Endpoint `POST /encuestas/seed/{cantidad}` en `main.py` para generar datos sinteticos.

## Validaciones ejecutadas
1. Validacion de implementacion:
   - Requisitos RF1-RF5 y RT1-RT5 cruzados con evidencia.
2. Validacion funcional:
   - Ejecucion de `pytest -q` con resultado `9 passed`.
