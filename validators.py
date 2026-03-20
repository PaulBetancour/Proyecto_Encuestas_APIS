from __future__ import annotations

from typing import Any
import re
import unicodedata

DEPARTAMENTOS_COLOMBIA = {
    "amazonas",
    "antioquia",
    "arauca",
    "atlantico",
    "bogota",
    "bolivar",
    "boyaca",
    "caldas",
    "caqueta",
    "casanare",
    "cauca",
    "cesar",
    "choco",
    "cordoba",
    "cundinamarca",
    "guainia",
    "guaviare",
    "huila",
    "la guajira",
    "magdalena",
    "meta",
    "narino",
    "norte de santander",
    "putumayo",
    "quindio",
    "risaralda",
    "san andres y providencia",
    "santander",
    "sucre",
    "tolima",
    "valle del cauca",
    "vaupes",
    "vichada",
}


def normalizar_texto(valor: Any) -> str:
    if not isinstance(valor, str):
        raise TypeError("El valor debe ser texto")

    valor = valor.strip()
    valor = re.sub(r"\s+", " ", valor)
    valor = unicodedata.normalize("NFD", valor)
    valor = "".join(ch for ch in valor if unicodedata.category(ch) != "Mn")
    return valor.lower()


def normalizar_departamento(valor: Any) -> str:
    dep = normalizar_texto(valor)
    if dep not in DEPARTAMENTOS_COLOMBIA:
        raise ValueError(
            "Departamento no valido para Colombia. Revise la ortografia y use un departamento oficial."
        )
    return dep.title()
