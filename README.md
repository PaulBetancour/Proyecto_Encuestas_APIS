# API de Gestión de Encuestas Poblacionales - Proyecto Completo

## 📋 La Historia: ¿Qué Hicimos?

Este proyecto nace de la necesidad de procesar, validar y analizar datos de encuestas poblacionales de manera robusta y estructurada. Imagina que tienes miles de respuestas de ciudadanos sobre satisfacción de servicios, datos del censo, o cualquier estudio estadístico. Necesitas una forma inteligente para:

1. **Recibir los datos** desde archivos CSV o peticiones HTTP
2. **Validarlos correctamente** (¿la edad tiene sentido? ¿el departamento existe en Colombia?)
3. **Almacenarlos ordenadamente** sin que se pierdan ni se corrompan
4. **Hacer preguntas a los datos** (¿cuántas encuestas por departamento? ¿promedio de edad?)
5. **Mostrar todo de forma clara** con documentación interactiva

Para lograr esto, construimos una **API REST modular** usando FastAPI, Pydantic y Python. Cada pieza tiene un propósito claro:

---

## 🎯 Objetivos del Proyecto (Según Rúbrica)

### Requisitos Funcionales (RF)
- **RF1**: Modelos complejos anidados con tipos avanzados (Union, Optional, List)
- **RF2**: Validadores de campo con lógica antes (`mode='before'`) y después (`mode='after'`) de asignación
- **RF3**: CRUD completo + estadísticas con códigos HTTP correctos (201, 200, 404, 204)
- **RF4**: Manejo personalizado de errores 422 con respuestas estructuradas y logging
- **RF5**: Al menos un endpoint asincrónico usando `async def` y conceptos ASGI

### Requisitos Técnicos (RT)
- **RT1**: Entorno virtual configurable con `requirements.txt`
- **RT2**: Control de versiones Git con rama `develop` + `main` y 5+ commits significativos
- **RT3**: Estructura modular del código (separación en archivos por responsabilidad)
- **RT4**: Documentación automática (Swagger UI `/docs` y Redoc `/redoc`)
- **RT5**: Decorador personalizado que agregue funcionalidad a endpoints

---

## 🏗️ Estructura del Proyecto

```
proyecto/
├── main.py                  # Punto de entrada, todos los endpoints
├── models.py               # Definición de modelos Pydantic (validación)
├── validators.py           # Funciones reutilizables de validación
├── database.py             # Capa en memoria (simula base de datos)
├── utils.py                # Decoradores y funciones auxiliares
├── requirements.txt        # Lista de dependencias
├── README.md              # Este archivo
├── .gitignore             # Archivos a ignorar en Git
├── data/entrada/          # Carpeta de entrada para archivos CSV
│   └── CNPV2018_1VIV_A2_11.CSV  # Tu archivo real de datos
└── tests/
    ├── test_models.py     # Pruebas de validación de modelos
    └── test_endpoints.py  # Pruebas de endpoints HTTP
```

---

## 🚀 Paso 1: Preparar el Entorno (RT1)

Antes de hacer cualquier cosa, necesitamos un espacio limpio y aislado para que Python instale todas las librerías que necesitamos:

```bash
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

¿Qué hace esto?
- **`python -m venv .venv`**: Crea un "contenedor virtual" llamado `.venv` en tu carpeta
- **`.\.venv\Scripts\Activate.ps1`**: Entra al contenedor (verás `(.venv)` al lado del prompt)
- **`pip install -r requirements.txt`**: Descarga todas las librerías necesarias (FastAPI, Pydantic, pytest, etc.)

---

## 🔧 Paso 2: Ejecutar la API

Una vez activado el entorno virtual:

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

¿Dónde va ahora?
- **Swagger (documentación interactiva)**: http://127.0.0.1:8000/docs
- **Redoc (otra vista de documentación)**: http://127.0.0.1:8000/redoc
- **Panel HTML de demostración**: http://127.0.0.1:8000/
  - En el panel hay un **selector de archivo** para subir tu CSV sin escribir código

Ver servidor ejecutse: **"Uvision running on http://127.0.0.1:8000"** = ¡Éxito!

---

## 📊 Los Endpoints Explicados

### 🔴 CRUD Genérico (Para encuestas normales)

Imaginemos que tienes una encuesta sobre satisfacción de un servicio con preguntas tipo: "¿Qué tan satisfecho estás?" (Likert 1-5) o "¿Qué porcentaje de disponibilidad?" (0-100).

**Crear una encuesta:**
```bash
POST /encuestas/
```
```json
{
  "encuestado": {
    "nombre": "Ana García",
    "edad": 34,
    "estrato": 3,
    "departamento": "Cundinamarca"
  },
  "respuestas": [
    {
      "pregunta_id": 1,
      "tipo_pregunta": "likert",
      "valor": 5,
      "comentario": "Excelente atención"
    },
    {
      "pregunta_id": 2,
      "tipo_pregunta": "porcentaje",
      "valor": 85.0,
      "comentario": null
    }
  ]
}
```

Respuesta: `201 Created` (la encuesta se guardó, recibió ID automático)

**Listar todas las encuestas:**
```bash
GET /encuestas/
```
Devuelve un array con todas las guardadas.

**Obtener una encuesta por ID:**
```bash
GET /encuestas/1
```
Devuelve la encuesta ID=1 (o 404 si no existe).

**Actualizar una encuesta:**
```bash
PUT /encuestas/1
```
Con el mismo JSON que POST, pero actualiza la existente.

**Eliminar una encuesta:**
```bash
DELETE /encuestas/1
```
Respuesta: `204 No Content` (eliminada, sin respuesta adicional).

**Ver estadísticas:**
```bash
GET /encuestas/estadisticas/
```
Devuelve: cantidad total, promedio de edad, conteo por estrato, por departamento, etc.

---

### 🟢 Endpoints Extras para Demo

**Generar datos de prueba (faker):**
```bash
POST /encuestas/seed/10
```
Crea 10 encuestas con nombres, edades, departamentos aleatorios (útil para demo sin CSV).

**Cargar desde CSV (genérico):**
```bash
POST /encuestas/csv/
```
Subes un archivo donde cada fila es una encuesta. Columns esperadas:
- `nombre, edad, estrato, departamento` (datos personales)
- `q1_tipo, q1_valor, q1_comentario, q2_tipo, q2_valor, q2_comentario` (respuestas)

Ejemplo de CSV:
```csv
nombre,edad,estrato,departamento,q1_tipo,q1_valor,q1_comentario,q2_tipo,q2_valor,q2_comentario
Ana Pérez,28,3,Antioquia,likert,5,Excelente,porcentaje,92.4,
Carlos López,45,2,Bogotá,likert,4,Bueno,porcentaje,78.0,
```

**Soporta aliases** (nombres de columnas alternativos):
- Para `nombre`: también acepta `name`, `nombres`, `encuestado_nombre`
- Para `edad`: también acepta `age`, `edad_anos`
- Para `estrato`: también acepta `estrato_socioeconomico`, `nivel_estrato`
- Para `departamento`: también acepta `depto`, `departamento_residencia`, `region`

---

### 🔵 Endpoints Especiales para Datos Reales (Como CNPV)

Aquí viene lo importante: Si tu CSV es del **Censo Nacional de Población y Vivienda (CNPV)** como `CNPV2018_1VIV_A2_11.CSV`, éste tiene una estructura diferente: es sobre **viviendas**, no personas. Las columnas son `U_DPTO`, `VA1_ESTRATO`, `U_VIVIENDA`, etc. ¡No tiene campos como "nombre" o "edad"!

Por eso creamos un endpoint especial que NO fuerza mapeo:

**Analizar base real CNPV:**
```bash
POST /datasets/cnpv/analizar/?max_filas=50000
```

Subes el archivo CNPV original. Respuesta:
```json
{
  "archivo": "CNPV2018_1VIV_A2_11.CSV",
  "columnas_detectadas": ["TIPO_REG", "U_DPTO", "U_MPIO", "UA_CLASE", "..."],
  "total_columnas": 30,
  "filas_procesadas": 2000,
  "filas_validas": 1837,
  "filas_invalidas": 163,
  "porcentaje_campos_vacios": 26.38,
  "estadisticas_numericas": {
    "V_TOT_HOG": {"count": 1837, "min": 1.0, "max": 6.0, "mean": 1.07},
    "VA1_ESTRATO": {"count": 1837, "min": 0.0, "max": 9.0, "mean": 2.92}
  },
  "resumen_campos_clave": {
    "U_DPTO": {"no_nulos": 2000, "top_valores": [{"codigo": "11", "etiqueta": "BOGOTA, D.C.", "conteo": 1837}]},
    "VA1_ESTRATO": {"no_nulos": 1837, "top_valores": [{"codigo": "2", "etiqueta": "Estrato 2", "conteo": 729}]}
  },
  "modelos_proyecto": {
    "ubicacion": {"campos": ["U_DPTO", "U_MPIO", "UA_CLASE"]},
    "vivienda_detalle": {"campos": ["VA1_ESTRATO", "V_MAT_PISO", "VF_INTERNET"]},
    "encuesta_hogar": {"campos": ["UVA_USO_UNIDAD", "V_TIPO_VIV", "V_TOT_HOG", "COD_ENCUESTAS"]}
  }
}
```

### 🧾 Diccionario CNPV (Variables y Categorías)

Este diccionario se usa en el backend para traducir códigos a etiquetas legibles y mostrar resultados correctos en el panel HTML y en Swagger.

| Variable | Significado | Categorías principales |
|---|---|---|
| `VA1_ESTRATO` | Estrato de la vivienda (según servicio de energía) | `0` Sin Estrato, `1` Estrato 1, `2` Estrato 2, `3` Estrato 3, `4` Estrato 4, `5` Estrato 5, `6` Estrato 6, `9` No sabe |
| `UA_CLASE` | Clase del asentamiento | `1` Cabecera Municipal, `2` Centro Poblado, `3` Rural Disperso, `4` Resto Rural |
| `UVA_USO_UNIDAD` | Uso de la unidad | `1` Vivienda, `2` Mixto, `3` Unidad no residencial, `4` LEA |
| `V_TIPO_VIV` | Tipo de vivienda | `1` Casa, `2` Apartamento, `3` Tipo cuarto, `4` Tradicional indígena, `5` Tradicional étnica, `6` Otro |
| `V_TOT_HOG` | Total de hogares en la vivienda | Valor numérico discreto (habitualmente `1` a `20+`) |
| `U_DPTO` | Departamento (código DANE) | `05` Antioquia, `08` Atlántico, `11` Bogotá D.C., ..., `99` Vichada |
| `U_MPIO` | Municipio (código DANE) | Código municipal de 3 dígitos |
| `V_MAT_PISO` | Material predominante de piso | `1` Mármol/madera, `2` Baldosa/vinilo, `3` Alfombra, `4` Cemento/gravilla, `5` Madera burda, `6` Tierra/arena/barro |
| `VF_INTERNET` | Servicio de internet en la vivienda | `1` Sí, `2` No |
| `COD_ENCUESTAS` | Código de encuesta/vivienda | Identificador numérico de registro |

### 🧩 Adaptación a los 3 modelos de la rúbrica

- **Modelo Ubicación**: `U_DPTO`, `U_MPIO`, `UA_CLASE`
- **Modelo ViviendaDetalle**: `VA1_ESTRATO`, `V_MAT_PISO`, `VF_INTERNET`
- **Modelo EncuestaHogar**: `UVA_USO_UNIDAD`, `V_TIPO_VIV`, `V_TOT_HOG`, `COD_ENCUESTAS`

Con esto, la API no intenta mapear las 30 columnas en un único formulario largo, sino que agrupa variables críticas para sustentar RF1 (modelos anidados), RF2 (validación) y RF3 (análisis).

**Consultar último reporte CNPV:**
```bash
GET /datasets/cnpv/ultimo/
```

Devuelve el resultado anterior sin tener que procesar de nuevo.

**¿Por qué dos endpoints?** Porque:
- `/encuestas/*` = Datos de personas con campos demográficos explícitos
- `/datasets/cnpv/*` = Datos de viviendas, estructura censal, sin inventar campos

---

## 🧪 El Corazón: Validación (RF1 + RF2)

### Modelos Anidados (RF1)

En `models.py` definimos tres modelos conectados:

```python
class Encuestado(BaseModel):
    nombre: str                        # Texto limpio
    edad: int                          # 0 a 120 años
    estrato: int                       # 1 a 6 (estratos socioeconómicos colombianos)
    departamento: str                  # Validado contra 32 reales de Colombia

class RespuestaEncuesta(BaseModel):
    pregunta_id: int
    tipo_pregunta:  Literal["likert", "porcentaje", "texto"]
    valor: Union[int, float, str]      # Puede ser 1-5, 0-100%, o texto
    comentario: Optional[str] = None

class EncuestaCompleta(BaseModel):
    id: Optional[int] = None
    fecha_registro: datetime
    encuestado: Encuestado              # 🔴 Modelo anidado
    respuestas: List[RespuestaEncuesta] # 🔴 Lista de modelos anidados
```

¿Por qué anidados? Porque reflejan la realidad: Una encuesta tiene **un encuestado** + **varias respuestas**. Si todo fuera plano, sería caos.

### Validadores Inteligentes (RF2)

**Antes de guardar** (`mode='before'`):
- Limpiar nombres: "  ana  " → "ana"
- Normalizar departamento: "bogotá" → "Bogota" (búsqueda case-insensitive)
- Descomponer Unicode para comparar sin tildes

**Después de guardar** (`mode='after'`):
- Verificar que edad es 0-120
- Verificar que valor Likert es 1-5
- Verificar que porcentaje es 0-100

```python
@field_validator('nombre', mode='before')
def limpiar_nombre(cls, v):
    return v.strip().lower()

@field_validator('edad', mode='after')
def validar_edad(cls, v):
    if not 0 <= v <= 120:
        raise ValueError('Edad debe estar entre 0 y 120')
    return v
```

---

## 🛡️ Manejo de Errores (RF4)

¿Qué pasa si envías datos malos?

```json
{
  "encuestado": {
    "nombre": "Ana",
    "edad": 250,           ❌ ¡250 años es imposible!
    "estrato": 7,          ❌ ¡No existe estrato 7!
    "departamento": "Marte" ❌ ¡No es departamento colombiano!
  },
  "respuestas": []
}
```

FastAPI + Pydantic generan automáticamente un error **422 Unprocessable Entity** con detalles:

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "encuestado", "edad"],
      "msg": "Edad debe estar entre 0 y 120",
      "input": 250
    },
    {
      "type": "value_error",
      "loc": ["body", "encuestado", "departamento"],
      "msg": "Departamento 'Marte' no encontrado...",
      "input": "Marte"
    }
  ]
}
```

**Además**, nuestro handler personalizado de 422 **registra el error** (RF4):
```
ERROR - Validación falló en POST /encuestas/: 2 errores en edad, departamento
```

---

## ⚙️ Decorador Personalizado (RT5)

En `utils.py` creamos un decorador `@log_request` que:
- Registra cuándo inicia una petición
- Mide cuánto tiempo tarda
- Registra cuándo termina

```python
@app.post("/encuestas/")
@log_request             # 👈 Lo aplicamos aquí
async def crear_encuesta(encuesta: EncuestaCompleta, request: Request):
    ...
```

En los logs ves:
```
INFO - [POST /encuestas/] iniciado
INFO - [POST /encuestas/] completado en 12.34ms
```

**¿Por qué?** Porque con microservicios y muchos usuarios, necesitas saber qué endpoints son lentos.

---

## 📈 Async/Await (RF5)

FastAPI usa **ASGI** (Asynchronous Server Gateway Interface), que permite que múltiples peticiones se ejecuten "al mismo tiempo":

```python
@app.get("/encuestas/")
async def listar_encuestas(request: Request):  # async def = puede esperar sin bloquear
    # Si esta función duerme 5 segundos, otros usuarios no se quedan esperando
    data = await database.listar()  # await = espera sin bloquear
    return data
```

Sin `async/await`, si un usuario hace query lenta, los demás se quedan congelados. ¡Desastre!

---

## 🧪 Tests (Bonus)

Corremos:
```bash
pytest -q
```

Output:
```
test_models.py::test_encuestado_valido PASSED
test_models.py::test_edad_invalida PASSED
test_endpoints.py::test_crear_encuesta_201 PASSED
test_endpoints.py::test_get_encuesta_404 PASSED
...
9 passed en 0.23s
```

¿Qué probamos?
- ¿Modelos rechazan datos inválidos?
- ¿Endpoints retornan códigos HTTP correctos?
- ¿Validadores funcionan?
- ¿CRUD completo?

---

## 📝 Git y Versionamiento (RT2)

Usamos dos ramas:
- **`develop`**: Donde desarrollamos (experimental)
- **`main`**: Versión estable (lista para entregar)

Historial de commits (mínimo 5):
```
1. Estructura inicial + dependencias
2. Modelos y validadores Pydantic
3. Endpoints CRUD + estadísticas
4. Handler 422 + decorador @log_request
5. Tests y CNPV analyzer
6. README completo y demo
```

Cada commit es visible en GitHub para que el profesor vea tu progreso.

---

## 🎤 Sustentación a Profesor (5-10 minutos)

Prepara esto:

1. **¿Por qué modelos anidados?**
   > "Porque una encuesta en la realidad tiene un encuestado + respuestas. Los modelos anidados representan esa estructura. Si todo fuera plano sería difícil validar y entender."

2. **¿`mode='before'` vs `mode='after'`?**
   > "`before` limpia datos antes de asignarlos (ej: trim whitespace). `after` valida después (ej: verificar que edad sea 0-120). Es un pipeline de limpieza + validación."

3. **¿HTTP 400 vs 422?**
   > "400 = Tu petición es malformada (JSON roto). 422 = Tu JSON es válido pero los datos no pasan validación de negocio (edad 250)."

4. **¿Por qué `async def`?**
   > "FastAPI usa ASGI que permite peticiones concurrentes. `async def` + `await` permiten que si una petición es lenta, otras no se 'congelen'. Es escalabilidad."

5. **¿El decorador `@log_request`?**
   > "Registra tiempo de ejecución de cada endpoint. Útil para identificar cuellos de botella en producción."

6. **¿Por qué dos endpoints de CSV?**
   > "Porque datos diferentes tienen estructuras diferentes. CNPV es sobre viviendas (columnas U_DPTO, VA1_ESTRATO), no personas. Endpoints separados evitan forzar mapeos incorrectos."

---

## 📂 Carpeta de Entrada (data/entrada/)

Aquí va tu archivo CSV real:
- `CNPV2018_1VIV_A2_11.CSV` (tu archivo de datos)

Cuando subes en `/datasets/cnpv/analizar/`, el endpoint lee desde aquí.

---

## 🎯 Resumen Rápido: ¿Qué Cumplimos?

| Sigla | Requisito | ✅ Hecho |
|-------|-----------|---------|
| **RF1** | Modelos anidados con tipos complejos | Sí: Union[int, float, str], Optional, List |
| **RF2** | Validadores before/after | Sí: mode='before' y mode='after' |
| **RF3** | CRUD + estadísticas | Sí: POST, GET, PUT, DELETE, /estadisticas |
| **RF4** | Error 422 personalizado | Sí: Handler con logging estructurado |
| **RF5** | Endpoint async | Sí: listarilestas con async def |
| **RT1** | Entorno virtual + requirements | Sí: .venv + requirements.txt |
| **RT2** | Git con develop + main | Sí: 6+ commits en GitHub |
| **RT3** | Modular (archivos separados) | Sí: main, models, validators, database, utils |
| **RT4** | Documentación automática | Sí: Swagger + Redoc |
| **RT5** | Decorador personalizado | Sí: @log_request con timing |

---

## 🎬 Listo para la Demo

El servidor está de pie. El código es limpio. Los tests pasan. ¡Ahora espero tu guion exacto de 5 minutos para que la demo salga perfecta! 🚀
