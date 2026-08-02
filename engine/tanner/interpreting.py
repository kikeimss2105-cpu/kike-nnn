"""Evaluación semántica de la fase Interpreting de Tanner.

A diferencia de Noticing (determinista, coincidencia exacta de IDs),
Interpreting evalúa si el estudiante relacionó los indicios en una
interpretación de texto libre — sin exigir frase literal ni vocabulario
único (ver caso YAML: no_exigir). Esto requiere comprensión semántica,
por lo que esta fase SÍ usa un modelo de lenguaje como colaborador.

Límites deliberados, consistentes con el contrato de seguridad del caso
(docs/casos/OBS-HTA-001_CONTRATO.md — "la IA no podrá cambiar la clave
clínica"):

- El LLM solo identifica PRESENCIA de conceptos/relaciones ya definidos
  en el YAML del caso. No puede inventar conceptos nuevos: cualquier cosa
  que reporte fuera del catálogo esperado se descarta antes de usarse.
- El LLM devuelve una estructura fija, no una calificación numérica ni
  una opinión libre — evita exactamente lo que el contrato prohíbe
  ("no se otorgará una puntuación arbitraria antes de validar la rúbrica").
- Si el LLM falla o responde algo no interpretable, el resultado se marca
  explícitamente como no confiable. Nunca se asume "todo bien" ni
  "todo mal" por un error técnico.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RespuestaClienteLLM:
    """Respuesta cruda del cliente de LLM, ya parseada a una forma fija."""

    conceptos_detectados: tuple[str, ...]
    relaciones_detectadas: tuple[str, ...]
    exitosa: bool
    detalle_error: str = ""


class ClienteInterpretacion(Protocol):
    """Contrato mínimo de cualquier cliente usado para evaluar Interpreting.

    Cualquier implementación (NVIDIA, OpenAI, un stub de pruebas) sirve
    mientras cumpla esta única función. Esto permite probar la lógica de
    evaluar_interpreting sin depender de una API externa real."""

    def identificar_conceptos_y_relaciones(
        self,
        texto_interpretacion: str,
        conceptos_minimos: tuple[str, ...],
        relaciones_esperadas: tuple[str, ...],
    ) -> RespuestaClienteLLM: ...


@dataclass(frozen=True, slots=True)
class ResultadoInterpreting:
    """Resultado explicable de la fase Interpreting."""

    conceptos_esperados: tuple[str, ...]
    conceptos_reconocidos: tuple[str, ...]
    conceptos_omitidos: tuple[str, ...]
    relaciones_esperadas: tuple[str, ...]
    relaciones_reconocidas: tuple[str, ...]
    relaciones_omitidas: tuple[str, ...]
    evaluacion_confiable: bool
    detalle_error: str = ""

    @property
    def completo_sin_errores(self) -> bool:
        return (
            self.evaluacion_confiable
            and not self.conceptos_omitidos
            and not self.relaciones_omitidas
        )


def evaluar_interpreting(
    conceptos_minimos: tuple[str, ...],
    relaciones_esperadas: tuple[str, ...],
    texto_interpretacion: str,
    cliente: ClienteInterpretacion,
) -> ResultadoInterpreting:
    """Evalúa la interpretación del estudiante usando un cliente LLM inyectado.

    No asigna calificación numérica. Si el cliente falla, el resultado se
    marca como no confiable en vez de asumir que la interpretación está
    bien o mal — un fallo técnico no debe traducirse en una nota."""

    texto_interpretacion = (texto_interpretacion or "").strip()

    if not texto_interpretacion:
        return ResultadoInterpreting(
            conceptos_esperados=conceptos_minimos,
            conceptos_reconocidos=(),
            conceptos_omitidos=conceptos_minimos,
            relaciones_esperadas=relaciones_esperadas,
            relaciones_reconocidas=(),
            relaciones_omitidas=relaciones_esperadas,
            evaluacion_confiable=True,
        )

    respuesta = cliente.identificar_conceptos_y_relaciones(
        texto_interpretacion, conceptos_minimos, relaciones_esperadas
    )

    if not respuesta.exitosa:
        return ResultadoInterpreting(
            conceptos_esperados=conceptos_minimos,
            conceptos_reconocidos=(),
            conceptos_omitidos=conceptos_minimos,
            relaciones_esperadas=relaciones_esperadas,
            relaciones_reconocidas=(),
            relaciones_omitidas=relaciones_esperadas,
            evaluacion_confiable=False,
            detalle_error=respuesta.detalle_error,
        )

    # Filtro de seguridad: solo se acepta lo que YA estaba en la lista
    # esperada del caso. El LLM no puede "inventar" haber detectado algo
    # fuera del catálogo definido por quien diseñó el caso.
    conceptos_validos = set(conceptos_minimos)
    relaciones_validas = set(relaciones_esperadas)

    conceptos_reconocidos = tuple(
        c for c in respuesta.conceptos_detectados if c in conceptos_validos
    )
    relaciones_reconocidas = tuple(
        r for r in respuesta.relaciones_detectadas if r in relaciones_validas
    )

    conceptos_omitidos = tuple(
        c for c in conceptos_minimos if c not in conceptos_reconocidos
    )
    relaciones_omitidas = tuple(
        r for r in relaciones_esperadas if r not in relaciones_reconocidas
    )

    return ResultadoInterpreting(
        conceptos_esperados=conceptos_minimos,
        conceptos_reconocidos=conceptos_reconocidos,
        conceptos_omitidos=conceptos_omitidos,
        relaciones_esperadas=relaciones_esperadas,
        relaciones_reconocidas=relaciones_reconocidas,
        relaciones_omitidas=relaciones_omitidas,
        evaluacion_confiable=True,
    )
