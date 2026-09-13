"""Servicios de alto nivel para ejecutar casos Tanner."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from engine.tanner.casos import CasoTanner, cargar_caso_tanner
from engine.tanner.interpreting import ClienteInterpretacion, ResultadoInterpreting, evaluar_interpreting
from engine.tanner.modelos import ResultadoNoticing
from engine.tanner.noticing import evaluar_noticing


@dataclass(frozen=True, slots=True)
class EjecucionNoticing:
    """Resultado completo de ejecutar Noticing sobre un caso YAML."""

    caso: CasoTanner
    resultado: ResultadoNoticing


def ejecutar_noticing_desde_caso(
    ruta_caso: str | Path,
    seleccionados: Iterable[str],
) -> EjecucionNoticing:
    """Carga un caso y evalúa la selección del estudiante.

    Esta función constituye la frontera entre una futura interfaz
    y el motor pedagógico. La interfaz no necesita cargar YAML ni
    construir manualmente los indicios.
    """

    caso = cargar_caso_tanner(ruta_caso)
    resultado = evaluar_noticing(
        caso.indicios_noticing,
        seleccionados,
    )

    return EjecucionNoticing(
        caso=caso,
        resultado=resultado,
    )


@dataclass(frozen=True, slots=True)
class EjecucionInterpreting:
    """Resultado completo de ejecutar Interpreting sobre un caso YAML."""

    caso: CasoTanner
    resultado: ResultadoInterpreting


def ejecutar_interpreting_desde_caso(
    ruta_caso: str | Path,
    texto_interpretacion: str,
    cliente: ClienteInterpretacion,
) -> EjecucionInterpreting:
    """Carga un caso y evalúa la interpretación del estudiante.

    Simétrico a ejecutar_noticing_desde_caso: es la frontera entre una
    futura interfaz y el motor pedagógico para la fase Interpreting.
    La interfaz no necesita cargar YAML ni conocer el contrato interno
    de evaluar_interpreting — solo entrega texto libre y un cliente.

    El cliente se recibe por parámetro (no se construye aquí) para no
    forzar una dependencia de red/credenciales dentro del motor
    pedagógico y para permitir pruebas con un cliente simulado.

    Si el caso no define conceptos/relaciones esperadas de Interpreting
    (conceptos_minimos_interpreting y relaciones_esperadas_interpreting
    vacíos — ver CasoTanner), la evaluación se ejecuta igual pero no
    tiene nada que reconocer u omitir: quien llame debe decidir si eso
    es un caso pensado solo para Noticing, no un error de esta función.
    Antes de exponer Interpreting a una interfaz real, revisar además
    inspeccionar_cierre_tanner (engine/tanner/cierre.py) para saber si
    el caso tiene autorización explícita para esa fase.
    """

    caso = cargar_caso_tanner(ruta_caso)
    resultado = evaluar_interpreting(
        caso.conceptos_minimos_interpreting,
        caso.relaciones_esperadas_interpreting,
        texto_interpretacion,
        cliente,
    )

    return EjecucionInterpreting(
        caso=caso,
        resultado=resultado,
    )
