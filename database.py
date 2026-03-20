from __future__ import annotations

from typing import Dict, List, Optional

from models import EncuestaCompleta

_db: Dict[int, EncuestaCompleta] = {}
_next_id = 1


def reset_db() -> None:
    global _db, _next_id
    _db = {}
    _next_id = 1


def create_encuesta(encuesta: EncuestaCompleta) -> EncuestaCompleta:
    global _next_id
    nueva = encuesta.model_copy(deep=True)
    nueva.id = _next_id
    _db[_next_id] = nueva
    _next_id += 1
    return nueva


def list_encuestas() -> List[EncuestaCompleta]:
    return list(_db.values())


def get_encuesta(encuesta_id: int) -> Optional[EncuestaCompleta]:
    return _db.get(encuesta_id)


def update_encuesta(encuesta_id: int, encuesta: EncuestaCompleta) -> Optional[EncuestaCompleta]:
    if encuesta_id not in _db:
        return None

    actualizada = encuesta.model_copy(deep=True)
    actualizada.id = encuesta_id
    _db[encuesta_id] = actualizada
    return actualizada


def delete_encuesta(encuesta_id: int) -> bool:
    if encuesta_id not in _db:
        return False
    del _db[encuesta_id]
    return True
