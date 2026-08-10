"""Cálculo puro del índice de Silverman-Andersen."""

from __future__ import annotations

from engine.neonatal.modelos import ResultadoEscalaNeonatal, validar_componentes


COMPONENTES_SILVERMAN = (
    "movimiento_toracoabdominal",
    "tiraje_intercostal",
    "retraccion_xifoidea",
    "aleteo_nasal",
    "quejido_espiratorio",
)


def calcular_silverman(
    movimiento_toracoabdominal: int | None,
    tiraje_intercostal: int | None,
    retraccion_xifoidea: int | None,
    aleteo_nasal: int | None,
    quejido_espiratorio: int | None,
) -> ResultadoEscalaNeonatal:
    """Calcula 0-10; no completa el cálculo con componentes ausentes."""

    valores = (movimiento_toracoabdominal, tiraje_intercostal, retraccion_xifoidea, aleteo_nasal, quejido_espiratorio)
    desglose = dict(zip(COMPONENTES_SILVERMAN, valores))
    permitidos = {nombre: frozenset((0, 1, 2)) for nombre in COMPONENTES_SILVERMAN}
    faltantes = validar_componentes(desglose, permitidos)
    if faltantes:
        return ResultadoEscalaNeonatal(
            "Silverman-Andersen", None, desglose, faltantes,
            "No calculado: faltan componentes por valorar.",
        )

    total = sum(valor for valor in desglose.values() if valor is not None)
    if total == 0:
        interpretacion = "Sin dificultad respiratoria (0)."
    elif total <= 3:
        interpretacion = "Dificultad respiratoria leve (1-3)."
    elif total <= 6:
        interpretacion = "Dificultad respiratoria moderada (4-6)."
    else:
        interpretacion = "Dificultad respiratoria grave (7-10)."
    return ResultadoEscalaNeonatal("Silverman-Andersen", total, desglose, (), interpretacion)
