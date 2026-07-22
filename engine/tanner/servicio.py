"""Servicios de alto nivel para ejecutar casos Tanner."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from engine.tanner.casos import CasoTanner, cargar_caso_tanner
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
