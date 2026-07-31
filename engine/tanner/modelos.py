"""Modelos de datos del motor Tanner.

Esta primera versión solo implementa contratos para la fase Noticing.
No contiene puntuaciones clínicas ni reglas farmacológicas.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CategoriaIndicio(str, Enum):
    """Clasificación pedagógica de un dato presentado en el caso."""

    CRITICO = "critico"
    RELEVANTE = "relevante"
    CONTEXTO_ESENCIAL = "contexto_esencial"
    COMPLEMENTARIO = "complementario"
    DATO_NO_PRIORITARIO = "dato_no_prioritario"
    CONTEXTO_NO_PRIORITARIO = "contexto_no_prioritario"


@dataclass(frozen=True, slots=True)
class IndicioTanner:
    """Dato clínico o contextual disponible durante Noticing."""

    id: str
    texto: str
    categoria: CategoriaIndicio
    esperado: bool
    fundamento: str

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("El indicio debe tener un identificador.")
        if not self.texto.strip():
            raise ValueError("El indicio debe contener texto.")
        if not self.fundamento.strip():
            raise ValueError("El indicio debe incluir un fundamento.")


@dataclass(frozen=True, slots=True)
class ResultadoNoticing:
    """Resultado explicable de la selección de indicios."""

    presentados: tuple[str, ...]
    seleccionados: tuple[str, ...]
    reconocidos_esperados: tuple[str, ...]
    omitidos_esperados: tuple[str, ...]
    omisiones_criticas: tuple[str, ...]
    seleccionados_no_prioritarios: tuple[str, ...]
    identificadores_desconocidos: tuple[str, ...]
    seleccion_repetida: tuple[str, ...]

    @property
    def tiene_omisiones_criticas(self) -> bool:
        return bool(self.omisiones_criticas)

    @property
    def seleccion_valida(self) -> bool:
        return not self.identificadores_desconocidos

    @property
    def completo_sin_errores(self) -> bool:
        return (
            self.seleccion_valida
            and not self.omitidos_esperados
            and not self.seleccionados_no_prioritarios
        )
