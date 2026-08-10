"""Capurro A (somático-neurológico) y B (somático), sin imputaciones."""

from __future__ import annotations

from engine.neonatal.modelos import ResultadoEscalaNeonatal, validar_componentes


_SOMATICOS = {
    "forma_oreja": frozenset((0, 8, 16, 24)),
    "tamano_glandula_mamaria": frozenset((0, 5, 10, 15)),
    "formacion_pezon": frozenset((0, 5, 10, 15)),
    "textura_piel": frozenset((0, 5, 10, 15, 20)),
}


def _resultado_capurro(
    variante: str,
    desglose: dict[str, int | None],
    permitidos: dict[str, frozenset[int]],
    constante: int,
) -> ResultadoEscalaNeonatal:
    faltantes = validar_componentes(desglose, permitidos)
    formula = f"({constante} + suma de componentes) / 7"
    if faltantes:
        return ResultadoEscalaNeonatal(
            f"Capurro {variante}", None, desglose, faltantes,
            "No calculado: faltan variables obligatorias.", formula,
        )

    puntos = sum(valor for valor in desglose.values() if valor is not None)
    dias_totales = constante + puntos
    semanas = dias_totales / 7
    return ResultadoEscalaNeonatal(
        escala=f"Capurro {variante}",
        total=puntos,
        desglose=desglose,
        datos_faltantes=(),
        interpretacion="Estimación de edad gestacional por método Capurro.",
        formula=formula,
        edad_gestacional_semanas=semanas,
        semanas_completas=dias_totales // 7,
        dias_adicionales=dias_totales % 7,
    )


def calcular_capurro_a(
    forma_oreja: int | None,
    tamano_glandula_mamaria: int | None,
    formacion_pezon: int | None,
    textura_piel: int | None,
    signo_bufanda: int | None,
    caida_cabeza: int | None,
) -> ResultadoEscalaNeonatal:
    """Calcula Capurro A: cuatro signos somáticos y dos neurológicos."""

    desglose = {
        "forma_oreja": forma_oreja,
        "tamano_glandula_mamaria": tamano_glandula_mamaria,
        "formacion_pezon": formacion_pezon,
        "textura_piel": textura_piel,
        "signo_bufanda": signo_bufanda,
        "caida_cabeza": caida_cabeza,
    }
    permitidos = {**_SOMATICOS, "signo_bufanda": frozenset((0, 6, 12, 18)), "caida_cabeza": frozenset((0, 4, 8, 12))}
    return _resultado_capurro("A", desglose, permitidos, 200)


def calcular_capurro_b(
    forma_oreja: int | None,
    tamano_glandula_mamaria: int | None,
    formacion_pezon: int | None,
    textura_piel: int | None,
    pliegues_plantares: int | None,
) -> ResultadoEscalaNeonatal:
    """Calcula Capurro B: cinco signos somáticos."""

    desglose = {
        "forma_oreja": forma_oreja,
        "tamano_glandula_mamaria": tamano_glandula_mamaria,
        "formacion_pezon": formacion_pezon,
        "textura_piel": textura_piel,
        "pliegues_plantares": pliegues_plantares,
    }
    permitidos = {**_SOMATICOS, "pliegues_plantares": frozenset((0, 5, 10, 15, 20))}
    return _resultado_capurro("B", desglose, permitidos, 204)
