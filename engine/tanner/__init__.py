"""Motor pedagógico basado en el Modelo de Juicio Clínico de Tanner."""

from engine.tanner.modelos import (
    CategoriaIndicio,
    IndicioTanner,
    ResultadoNoticing,
)
from engine.tanner.noticing import evaluar_noticing

__all__ = [
    "CategoriaIndicio",
    "IndicioTanner",
    "ResultadoNoticing",
    "evaluar_noticing",
]
