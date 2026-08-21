"""Escalas neonatales deterministas de KIKE-NNN."""

from engine.neonatal.apgar import calcular_apgar
from engine.neonatal.capurro import calcular_capurro_a, calcular_capurro_b
from engine.neonatal.modelos import ResultadoEscalaNeonatal
from engine.neonatal.servicio import calcular_escala, serializar_resultado
from engine.neonatal.silverman import calcular_silverman

__all__ = [
    "ResultadoEscalaNeonatal",
    "calcular_apgar",
    "calcular_capurro_a",
    "calcular_capurro_b",
    "calcular_escala",
    "calcular_silverman",
    "serializar_resultado",
]
