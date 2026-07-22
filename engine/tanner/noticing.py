"""Evaluación determinista de la fase Noticing de Tanner."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from engine.tanner.modelos import (
    CategoriaIndicio,
    IndicioTanner,
    ResultadoNoticing,
)


_CATEGORIAS_NO_PRIORITARIAS = {
    CategoriaIndicio.DATO_NO_PRIORITARIO,
    CategoriaIndicio.CONTEXTO_NO_PRIORITARIO,
}


def evaluar_noticing(
    indicios: Iterable[IndicioTanner],
    seleccionados: Iterable[str],
) -> ResultadoNoticing:
    """Evalúa qué indicios reconoció u omitió el estudiante.

    La función no asigna una calificación numérica. Conserva la
    trazabilidad de la selección y devuelve categorías explicables.
    """

    lista_indicios = tuple(indicios)
    ids_presentados = tuple(indicio.id for indicio in lista_indicios)

    if len(ids_presentados) != len(set(ids_presentados)):
        raise ValueError("Los identificadores de indicios deben ser únicos.")

    por_id = {indicio.id: indicio for indicio in lista_indicios}

    seleccion_original = tuple(
        identificador.strip()
        for identificador in seleccionados
        if identificador is not None and identificador.strip()
    )

    conteo = Counter(seleccion_original)
    seleccion_repetida = tuple(
        identificador
        for identificador, cantidad in conteo.items()
        if cantidad > 1
    )

    seleccion_unica = tuple(dict.fromkeys(seleccion_original))

    identificadores_desconocidos = tuple(
        identificador
        for identificador in seleccion_unica
        if identificador not in por_id
    )

    seleccion_conocida = tuple(
        identificador
        for identificador in seleccion_unica
        if identificador in por_id
    )

    esperados = tuple(
        indicio.id
        for indicio in lista_indicios
        if indicio.esperado
    )

    reconocidos_esperados = tuple(
        identificador
        for identificador in esperados
        if identificador in seleccion_conocida
    )

    omitidos_esperados = tuple(
        identificador
        for identificador in esperados
        if identificador not in seleccion_conocida
    )

    omisiones_criticas = tuple(
        identificador
        for identificador in omitidos_esperados
        if por_id[identificador].categoria == CategoriaIndicio.CRITICO
    )

    seleccionados_no_prioritarios = tuple(
        identificador
        for identificador in seleccion_conocida
        if por_id[identificador].categoria in _CATEGORIAS_NO_PRIORITARIAS
    )

    return ResultadoNoticing(
        presentados=ids_presentados,
        seleccionados=seleccion_conocida,
        reconocidos_esperados=reconocidos_esperados,
        omitidos_esperados=omitidos_esperados,
        omisiones_criticas=omisiones_criticas,
        seleccionados_no_prioritarios=seleccionados_no_prioritarios,
        identificadores_desconocidos=identificadores_desconocidos,
        seleccion_repetida=seleccion_repetida,
    )
