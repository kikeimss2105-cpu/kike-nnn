"""Cálculo puro de APGAR a partir de sus cinco puntajes observados."""

from __future__ import annotations

from engine.neonatal.modelos import ResultadoEscalaNeonatal, validar_componentes


COMPONENTES_APGAR = (
    "apariencia",
    "pulso",
    "gesticulacion",
    "actividad",
    "respiracion",
)


def calcular_apgar(
    apariencia: int | None,
    pulso: int | None,
    gesticulacion: int | None,
    actividad: int | None,
    respiracion: int | None,
) -> ResultadoEscalaNeonatal:
    """Calcula APGAR; cada componente debe ser 0, 1, 2 o ``None``."""

    desglose = dict(zip(COMPONENTES_APGAR, (apariencia, pulso, gesticulacion, actividad, respiracion)))
    permitidos = {nombre: frozenset((0, 1, 2)) for nombre in COMPONENTES_APGAR}
    faltantes = validar_componentes(desglose, permitidos)
    if faltantes:
        return ResultadoEscalaNeonatal(
            escala="APGAR",
            total=None,
            desglose=desglose,
            datos_faltantes=faltantes,
            interpretacion="No calculado: faltan componentes por valorar.",
        )

    total = sum(valor for valor in desglose.values() if valor is not None)
    if total >= 7:
        interpretacion = "Resultado tranquilizador (7-10) a los 5 minutos."
    elif total >= 4:
        interpretacion = "Resultado moderadamente anormal (4-6) a los 5 minutos."
    else:
        interpretacion = "Resultado bajo (0-3) a los 5 minutos."
    return ResultadoEscalaNeonatal("APGAR", total, desglose, (), interpretacion)
