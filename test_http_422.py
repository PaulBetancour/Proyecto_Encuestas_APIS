"""
Pruebas para validar que la API retorna HTTP 422 (Unprocessable Entity)
cuando recibe datos inválidos que violan las reglas de validación.
"""

import httpx
import json

BASE_URL = "http://127.0.0.1:8000"


def print_section(titulo):
    """Imprime título de sección."""
    print(f"\n{'='*70}")
    print(f"🔍 {titulo}")
    print(f"{'='*70}\n")


def test_422_response(caso_nombre, payload):
    """
    Envía un payload y valida que retorne HTTP 422.
    """
    print(f"📋 Caso: {caso_nombre}")
    print(f"📤 Payload:\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n")

    try:
        response = httpx.post(f"{BASE_URL}/encuestas/", json=payload, timeout=10)
        
        if response.status_code == 422:
            print(f"✅ HTTP 422 - Validación correcta")
            errors = response.json()
            print(f"📊 Respuesta:\n{json.dumps(errors, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ HTTP {response.status_code} - Se esperaba 422")
            print(f"📊 Respuesta:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
    
    print()


def main():
    print("\n" + "="*70)
    print("🧪 PRUEBAS DE HTTP 422 - VALIDACIÓN DE ERRORES")
    print("="*70)
    print("Esta suite de pruebas verifica que la API retorna HTTP 422")
    print("cuando recibe datos inválidos según las reglas Pydantic.\n")

    # ==================== CASOS: Encuestado ====================
    print_section("1️⃣ VALIDACIONES DEL ENCUESTADO")

    # Caso 1: Nombre muy corto (< 3 caracteres)
    test_422_response(
        "FALLA: Nombre muy corto (< 3 caracteres)",
        {
            "encuestado": {
                "nombre": "Jo",  # Error: min_length=3
                "edad": 30,
                "estrato": 3,
                "departamento": "Bogota"
            },
            "respuestas": [
                {"pregunta_id": 1, "tipo_pregunta": "likert", "valor": 3}
            ]
        }
    )

    # Caso 2: Nombre muy largo (> 80 caracteres)
    test_422_response(
        "FALLA: Nombre muy largo (> 80 caracteres)",
        {
            "encuestado": {
                "nombre": "A" * 81,  # Error: max_length=80
                "edad": 30,
                "estrato": 3,
                "departamento": "Bogota"
            },
            "respuestas": [
                {"pregunta_id": 1, "tipo_pregunta": "likert", "valor": 3}
            ]
        }
    )

    # Caso 3: Edad fuera de rango (< 0)
    test_422_response(
        "FALLA: Edad negativa (< 0)",
        {
            "encuestado": {
                "nombre": "Juan Perez",
                "edad": -5,  # Error: ge=0
                "estrato": 3,
                "departamento": "Bogota"
            },
            "respuestas": [
                {"pregunta_id": 1, "tipo_pregunta": "likert", "valor": 3}
            ]
        }
    )

    # Caso 4: Edad fuera de rango (> 120)
    test_422_response(
        "FALLA: Edad mayor a 120 años",
        {
            "encuestado": {
                "nombre": "Juan Perez",
                "edad": 150,  # Error: le=120
                "estrato": 3,
                "departamento": "Bogota"
            },
            "respuestas": [
                {"pregunta_id": 1, "tipo_pregunta": "likert", "valor": 3}
            ]
        }
    )

    # Caso 5: Estrato inválido (< 1)
    test_422_response(
        "FALLA: Estrato menor a 1",
        {
            "encuestado": {
                "nombre": "Juan Perez",
                "edad": 30,
                "estrato": 0,  # Error: ge=1
                "departamento": "Bogota"
            },
            "respuestas": [
                {"pregunta_id": 1, "tipo_pregunta": "likert", "valor": 3}
            ]
        }
    )

    # Caso 6: Estrato inválido (> 6)
    test_422_response(
        "FALLA: Estrato mayor a 6",
        {
            "encuestado": {
                "nombre": "Juan Perez",
                "edad": 30,
                "estrato": 7,  # Error: le=6
                "departamento": "Bogota"
            },
            "respuestas": [
                {"pregunta_id": 1, "tipo_pregunta": "likert", "valor": 3}
            ]
        }
    )

    # ==================== CASOS: RespuestaEncuesta ====================
    print_section("2️⃣ VALIDACIONES DE RESPUESTAS")

    # Caso 7: Likert fuera de rango (< 1)
    test_422_response(
        "FALLA: Likert menor a 1",
        {
            "encuestado": {
                "nombre": "Juan Perez",
                "edad": 30,
                "estrato": 3,
                "departamento": "Bogota"
            },
            "respuestas": [
                {"pregunta_id": 1, "tipo_pregunta": "likert", "valor": 0}  # Error: debe estar 1-5
            ]
        }
    )

    # Caso 8: Likert fuera de rango (> 5)
    test_422_response(
        "FALLA: Likert mayor a 5",
        {
            "encuestado": {
                "nombre": "Juan Perez",
                "edad": 30,
                "estrato": 3,
                "departamento": "Bogota"
            },
            "respuestas": [
                {"pregunta_id": 1, "tipo_pregunta": "likert", "valor": 10}  # Error: debe estar 1-5
            ]
        }
    )

    # Caso 9: Likert no es entero
    test_422_response(
        "FALLA: Likert con decimal",
        {
            "encuestado": {
                "nombre": "Juan Perez",
                "edad": 30,
                "estrato": 3,
                "departamento": "Bogota"
            },
            "respuestas": [
                {"pregunta_id": 1, "tipo_pregunta": "likert", "valor": 3.5}  # Error: debe ser entero
            ]
        }
    )

    # Caso 10: Porcentaje negativo
    test_422_response(
        "FALLA: Porcentaje negativo",
        {
            "encuestado": {
                "nombre": "Juan Perez",
                "edad": 30,
                "estrato": 3,
                "departamento": "Bogota"
            },
            "respuestas": [
                {"pregunta_id": 1, "tipo_pregunta": "porcentaje", "valor": -10}  # Error: debe estar 0-100
            ]
        }
    )

    # Caso 11: Porcentaje mayor a 100
    test_422_response(
        "FALLA: Porcentaje mayor a 100",
        {
            "encuestado": {
                "nombre": "Juan Perez",
                "edad": 30,
                "estrato": 3,
                "departamento": "Bogota"
            },
            "respuestas": [
                {"pregunta_id": 1, "tipo_pregunta": "porcentaje", "valor": 150}  # Error: debe estar 0-100
            ]
        }
    )

    # Caso 12: Tipo de pregunta inválido
    test_422_response(
        "FALLA: Tipo de pregunta no válido",
        {
            "encuestado": {
                "nombre": "Juan Perez",
                "edad": 30,
                "estrato": 3,
                "departamento": "Bogota"
            },
            "respuestas": [
                {"pregunta_id": 1, "tipo_pregunta": "invalido", "valor": 3}  # Error: debe ser likert/porcentaje/texto
            ]
        }
    )

    # Caso 13: Texto vacío
    test_422_response(
        "FALLA: Respuesta de texto vacía",
        {
            "encuestado": {
                "nombre": "Juan Perez",
                "edad": 30,
                "estrato": 3,
                "departamento": "Bogota"
            },
            "respuestas": [
                {"pregunta_id": 1, "tipo_pregunta": "texto", "valor": ""}  # Error: texto no puede estar vacío
            ]
        }
    )

    # ==================== CASOS: EncuestaCompleta ====================
    print_section("3️⃣ VALIDACIONES DE ENCUESTA COMPLETA")

    # Caso 14: Sin respuestas (lista vacía)
    test_422_response(
        "FALLA: Sin respuestas (min_length=1)",
        {
            "encuestado": {
                "nombre": "Juan Perez",
                "edad": 30,
                "estrato": 3,
                "departamento": "Bogota"
            },
            "respuestas": []  # Error: debe tener al menos 1 respuesta
        }
    )

    # Caso 15: Preguntas duplicadas
    test_422_response(
        "FALLA: Preguntas con ID duplicados",
        {
            "encuestado": {
                "nombre": "Juan Perez",
                "edad": 30,
                "estrato": 3,
                "departamento": "Bogota"
            },
            "respuestas": [
                {"pregunta_id": 1, "tipo_pregunta": "likert", "valor": 3},
                {"pregunta_id": 1, "tipo_pregunta": "likert", "valor": 4}  # Error: pregunta_id duplicado
            ]
        }
    )

    # ==================== CASO VÁLIDO (Debe ser 201) ====================
    print_section("✅ CASO VÁLIDO (Debe retornar HTTP 201)")

    print("📋 Caso: Encuesta válida")
    valid_payload = {
        "encuestado": {
            "nombre": "Juan Perez",
            "edad": 30,
            "estrato": 3,
            "departamento": "Bogota"
        },
        "respuestas": [
            {"pregunta_id": 1, "tipo_pregunta": "likert", "valor": 4, "comentario": "Bueno"},
            {"pregunta_id": 2, "tipo_pregunta": "porcentaje", "valor": 85.5, "comentario": "Aceptable"},
            {"pregunta_id": 3, "tipo_pregunta": "texto", "valor": "Buen servicio", "comentario": "Recomendado"}
        ]
    }
    print(f"📤 Payload:\n{json.dumps(valid_payload, indent=2, ensure_ascii=False)}\n")

    try:
        response = httpx.post(f"{BASE_URL}/encuestas/", json=valid_payload, timeout=10)

        if response.status_code == 201:
            print(f"✅ HTTP 201 - Encuesta creada exitosamente")
            result = response.json()
            print(f"📊 Respuesta:\n{json.dumps(result, indent=2, ensure_ascii=False, default=str)}")
        else:
            print(f"❌ HTTP {response.status_code} - Se esperaba 201")
            print(f"📊 Respuesta:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

    # Resumen final
    print_section("📊 RESUMEN DE PRUEBAS")
    print("✔️ Se ejecutaron 16 pruebas de validación HTTP 422")
    print("✔️ Si todos los casos muestran '✅ HTTP 422', la validación funciona correctamente")
    print("✔️ El caso válido debe mostrar '✅ HTTP 201 - Encuesta creada exitosamente'\n")


if __name__ == "__main__":
    print("\n⚠️  NOTA: Asegúrate de que el servidor FastAPI esté corriendo en http://127.0.0.1:8000")
    print("💡 Ejecuta: python main.py   o   uvicorn main:app --reload\n")
    
    input("Presiona ENTER para comenzar las pruebas...")
    main()
