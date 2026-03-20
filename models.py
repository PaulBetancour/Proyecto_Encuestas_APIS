from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from validators import normalizar_departamento, normalizar_texto


class Encuestado(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nombre": "Paul Betancour",
                "edad": 25,
                "estrato": 3,
                "departamento": "Antioquia",
            }
        }
    )

    nombre: str = Field(min_length=3, max_length=80, description="Nombre completo del encuestado")
    edad: int = Field(ge=0, le=120, description="Edad biologica en anos")
    estrato: int = Field(ge=1, le=6, description="Estrato socioeconomico colombiano")
    departamento: str = Field(description="Departamento de residencia")

    @field_validator("nombre", mode="before")
    @classmethod
    def limpiar_nombre(cls, valor: object) -> str:
        limpio = normalizar_texto(valor)
        return " ".join(part.capitalize() for part in limpio.split(" "))

    @field_validator("departamento", mode="before")
    @classmethod
    def validar_departamento(cls, valor: object) -> str:
        return normalizar_departamento(valor)

    @field_validator("estrato", mode="after")
    @classmethod
    def validar_estrato_entero(cls, valor: int) -> int:
        if not isinstance(valor, int):
            raise ValueError("El estrato debe ser entero entre 1 y 6")
        return valor


class RespuestaEncuesta(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"pregunta_id": 1, "tipo_pregunta": "likert", "valor": 5, "comentario": "Excelente"},
                {"pregunta_id": 2, "tipo_pregunta": "porcentaje", "valor": 86.5, "comentario": None},
                {"pregunta_id": 3, "tipo_pregunta": "texto", "valor": "Muy buen servicio", "comentario": "Rapido"},
            ]
        }
    )

    pregunta_id: int = Field(ge=1, description="Identificador de pregunta")
    tipo_pregunta: Literal["likert", "porcentaje", "texto"] = Field(description="Tipo de variable de respuesta")
    valor: Union[int, float, str] = Field(description="Valor de respuesta")
    comentario: Optional[str] = Field(default=None, description="Comentario opcional")

    @field_validator("valor", mode="before")
    @classmethod
    def normalizar_valor_entrada(cls, valor: object, info: ValidationInfo) -> object:
        tipo = info.data.get("tipo_pregunta")
        if tipo in {"likert", "porcentaje"} and isinstance(valor, str):
            txt = valor.strip().replace(",", ".")
            try:
                return float(txt)
            except ValueError as exc:
                raise ValueError("Para preguntas numericas, el valor debe ser numerico") from exc
        return valor

    @field_validator("valor", mode="after")
    @classmethod
    def validar_valor_por_tipo(cls, valor: Union[int, float, str], info: ValidationInfo) -> Union[int, float, str]:
        tipo = info.data.get("tipo_pregunta")

        if tipo == "likert":
            if not isinstance(valor, (int, float)):
                raise ValueError("La respuesta Likert debe ser numerica")
            if not float(valor).is_integer() or not (1 <= int(valor) <= 5):
                raise ValueError("La escala Likert solo permite enteros del 1 al 5")
            return int(valor)

        if tipo == "porcentaje":
            if not isinstance(valor, (int, float)):
                raise ValueError("La respuesta de porcentaje debe ser numerica")
            val = float(valor)
            if not (0.0 <= val <= 100.0):
                raise ValueError("El porcentaje debe estar entre 0.0 y 100.0")
            return round(val, 2)

        if tipo == "texto":
            if not isinstance(valor, str) or not valor.strip():
                raise ValueError("Las preguntas de texto requieren una cadena no vacia")
            return valor.strip()

        return valor


class EncuestaCompleta(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "encuestado": {
                    "nombre": "Paul Betancour",
                    "edad": 25,
                    "estrato": 3,
                    "departamento": "Antioquia",
                },
                "respuestas": [
                    {"pregunta_id": 1, "tipo_pregunta": "likert", "valor": 4, "comentario": "Buena atencion"},
                    {"pregunta_id": 2, "tipo_pregunta": "porcentaje", "valor": 92.3, "comentario": None},
                    {"pregunta_id": 3, "tipo_pregunta": "texto", "valor": "Volveria", "comentario": ""},
                ],
            }
        }
    )

    id: Optional[int] = Field(default=None, description="Identificador interno autogenerado")
    fecha_registro: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Fecha UTC de registro")
    encuestado: Encuestado
    respuestas: list[RespuestaEncuesta] = Field(min_length=1, description="Lista de respuestas del encuestado")

    @model_validator(mode="after")
    def validar_preguntas_unicas(self) -> "EncuestaCompleta":
        ids = [r.pregunta_id for r in self.respuestas]
        if len(set(ids)) != len(ids):
            raise ValueError("No se permiten pregunta_id duplicados en una misma encuesta")
        return self


class EstadisticasEncuesta(BaseModel):
    total_encuestas: int
    promedio_edad: float
    distribucion_por_estrato: dict[int, int]
