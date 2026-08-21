"""Fachada mínima del engine neonatal, independiente de Streamlit."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from engine.neonatal.apgar import calcular_apgar
from engine.neonatal.capurro import calcular_capurro_a, calcular_capurro_b
from engine.neonatal.modelos import ResultadoEscalaNeonatal
from engine.neonatal.silverman import calcular_silverman


CALCULADORES = {
    "apgar": calcular_apgar,
    "silverman": calcular_silverman,
    "silverman-andersen": calcular_silverman,
    "capurro_a": calcular_capurro_a,
    "capurro_b": calcular_capurro_b,
}


def serializar_resultado(
    resultado: ResultadoEscalaNeonatal,
) -> dict[str, Any]:
    """Convierte un resultado en datos auditables sin imputar ausencias.

    Los componentes no valorados y los totales no calculados permanecen como
    ``None``. Esta función no interpreta ni reclasifica el resultado.
    """

    return {
        "escala": resultado.escala,
        "calculado": resultado.calculado,
        "total": resultado.total,
        "componentes": dict(resultado.componentes),
        "datos_faltantes": list(resultado.datos_faltantes),
        "interpretacion": resultado.interpretacion,
        "formula": resultado.formula,
        "edad_gestacional_semanas": resultado.edad_gestacional_semanas,
        "semanas_completas": resultado.semanas_completas,
        "dias_adicionales": resultado.dias_adicionales,
    }


def calcular_escala(nombre: str, datos: Mapping[str, Any]) -> ResultadoEscalaNeonatal:
    """Despacha una escala conocida sin modificar ni completar los datos."""

    clave = nombre.strip().lower()
    try:
        calculador = CALCULADORES[clave]
    except KeyError as error:
        raise ValueError(f"Escala neonatal no soportada: {nombre}.") from error
    return calculador(**dict(datos))
