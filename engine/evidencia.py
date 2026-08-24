"""Modelo auditable de evidencia clínica para el motor educativo.

Este módulo no establece precedencia clínica entre fuentes. Solo conserva
procedencia, polaridad y trazabilidad para que el motor no confunda una
mención textual negada con un hallazgo positivo.
"""

from dataclasses import dataclass
from enum import Enum


class FuenteEvidencia(str, Enum):
    MEDIDO = "MEDIDO"
    OBSERVADO = "OBSERVADO"
    REFERIDO_ESTRUCTURADO = "REFERIDO_ESTRUCTURADO"
    REFERIDO_TEXTO = "REFERIDO_TEXTO"
    INFERIDO = "INFERIDO"
    GENERADO_SISTEMA = "GENERADO_SISTEMA"


class PolaridadEvidencia(str, Enum):
    POSITIVA = "POSITIVA"
    NEGADA = "NEGADA"
    INCIERTA = "INCIERTA"
    NO_CONFIABLE = "NO_CONFIABLE"


class ConfiabilidadEvidencia(str, Enum):
    CONFIABLE = "CONFIABLE"
    NO_CONFIABLE = "NO_CONFIABLE"


@dataclass(frozen=True)
class EvidenciaClinica:
    concepto: str
    texto_original: str
    fuente: FuenteEvidencia | str
    polaridad: PolaridadEvidencia | str
    confiabilidad: ConfiabilidadEvidencia | str
    origen: str
    inicio: int | None = None
    fin: int | None = None
    derivada_de: str | None = None

    @property
    def puntuable(self) -> bool:
        return (
            str(self.polaridad) in {
                PolaridadEvidencia.POSITIVA.value,
                str(PolaridadEvidencia.POSITIVA),
            }
            and str(self.confiabilidad) in {
                ConfiabilidadEvidencia.CONFIABLE.value,
                str(ConfiabilidadEvidencia.CONFIABLE),
            }
        )


@dataclass(frozen=True)
class ResultadoParsing:
    evidencias: tuple[EvidenciaClinica, ...]
    estado: str = "PARSING_CONFIABLE"


def evidencia_estructurada(
    concepto: str,
    *,
    fuente: FuenteEvidencia | str,
    origen: str,
    derivada_de: str | None = None,
    texto_original: str | None = None,
) -> EvidenciaClinica:
    """Construye una evidencia positiva sin inferir prioridad entre fuentes."""
    return EvidenciaClinica(
        concepto=str(concepto),
        texto_original=str(texto_original if texto_original is not None else concepto),
        fuente=fuente,
        polaridad=PolaridadEvidencia.POSITIVA,
        confiabilidad=ConfiabilidadEvidencia.CONFIABLE,
        origen=origen,
        derivada_de=derivada_de,
    )


def evidencias_desde_hallazgos(
    hallazgos,
    *,
    fuente: FuenteEvidencia | str,
    origen: str,
    derivada_de: str | None = None,
) -> list[EvidenciaClinica]:
    """Adaptador temporal para listas estructuradas de la aplicación."""
    return [
        evidencia_estructurada(
            hallazgo,
            fuente=fuente,
            origen=origen,
            derivada_de=derivada_de,
        )
        for hallazgo in (hallazgos or [])
        if str(hallazgo).strip()
    ]
