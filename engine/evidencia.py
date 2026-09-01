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


class NaturalezaEvidencia(str, Enum):
    DATO_PRIMARIO_MEDIDO = "DATO_PRIMARIO_MEDIDO"
    DATO_PRIMARIO_OBSERVADO = "DATO_PRIMARIO_OBSERVADO"
    DATO_PRIMARIO_REFERIDO = "DATO_PRIMARIO_REFERIDO"
    DERIVACION_DETERMINISTA = "DERIVACION_DETERMINISTA"
    CONTEXTO = "CONTEXTO"
    INTERPRETACION = "INTERPRETACION"
    ALERTA = "ALERTA"
    SALIDA_SISTEMA = "SALIDA_SISTEMA"
    CONCLUSION_DIAGNOSTICA = "CONCLUSION_DIAGNOSTICA"
    LEGACY_NO_CLASIFICADO = "LEGACY_NO_CLASIFICADO"


class EstadoValidacion(str, Enum):
    VALIDADO = "VALIDADO"
    PENDIENTE_VALIDACION = "PENDIENTE_VALIDACION"
    LEGACY = "LEGACY"
    RETIRADO = "RETIRADO"


class ElegibilidadEvidencia(str, Enum):
    PUNTUABLE = "PUNTUABLE"
    NO_PUNTUABLE = "NO_PUNTUABLE"
    PROHIBIDA_AUTORREFERENCIA = "PROHIBIDA_AUTORREFERENCIA"


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
    id_dato_primario: str | None = None
    naturaleza: NaturalezaEvidencia | str = NaturalezaEvidencia.LEGACY_NO_CLASIFICADO
    estado_validacion: EstadoValidacion | str = EstadoValidacion.LEGACY
    elegibilidad: ElegibilidadEvidencia | str = ElegibilidadEvidencia.PUNTUABLE

    @property
    def puntuable(self) -> bool:
        fuente = getattr(self.fuente, "value", self.fuente)
        naturaleza = getattr(self.naturaleza, "value", self.naturaleza)
        estado_validacion = getattr(self.estado_validacion, "value", self.estado_validacion)
        elegibilidad = getattr(self.elegibilidad, "value", self.elegibilidad)
        base_valida = (
            str(self.polaridad) in {
                PolaridadEvidencia.POSITIVA.value,
                str(PolaridadEvidencia.POSITIVA),
            }
            and str(self.confiabilidad) in {
                ConfiabilidadEvidencia.CONFIABLE.value,
                str(ConfiabilidadEvidencia.CONFIABLE),
            }
            and elegibilidad == ElegibilidadEvidencia.PUNTUABLE.value
            and estado_validacion not in {
                EstadoValidacion.PENDIENTE_VALIDACION.value,
                EstadoValidacion.RETIRADO.value,
            }
            and naturaleza not in {
                NaturalezaEvidencia.CONTEXTO.value,
                NaturalezaEvidencia.INTERPRETACION.value,
                NaturalezaEvidencia.ALERTA.value,
                NaturalezaEvidencia.SALIDA_SISTEMA.value,
                NaturalezaEvidencia.CONCLUSION_DIAGNOSTICA.value,
                NaturalezaEvidencia.LEGACY_NO_CLASIFICADO.value,
            }
        )
        if not base_valida:
            return False

        # I24: una derivación solo puede puntuar bajo un contrato explícito:
        # regla validada, progenitor trazable y elegibilidad PUNTUABLE.
        if naturaleza == NaturalezaEvidencia.DERIVACION_DETERMINISTA.value:
            return (
                estado_validacion == EstadoValidacion.VALIDADO.value
                and bool(self.derivada_de or self.id_dato_primario)
                and elegibilidad == ElegibilidadEvidencia.PUNTUABLE.value
            )

        # I25: compatibilidad temporal exclusiva para datos primarios directos.
        # Las rutas observacionales históricas aún no tienen ID por checkbox;
        # inferencias y salidas generadas no reciben esta excepción.
        fuentes_directas = {
            FuenteEvidencia.MEDIDO.value,
            FuenteEvidencia.OBSERVADO.value,
            FuenteEvidencia.REFERIDO_ESTRUCTURADO.value,
            FuenteEvidencia.REFERIDO_TEXTO.value,
        }
        naturalezas_primarias = {
            NaturalezaEvidencia.DATO_PRIMARIO_MEDIDO.value,
            NaturalezaEvidencia.DATO_PRIMARIO_OBSERVADO.value,
            NaturalezaEvidencia.DATO_PRIMARIO_REFERIDO.value,
        }
        if naturaleza in naturalezas_primarias and fuente in fuentes_directas:
            return True

        return bool(self.id_dato_primario or self.derivada_de)


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
    id_dato_primario: str | None = None,
    naturaleza: NaturalezaEvidencia | str = NaturalezaEvidencia.LEGACY_NO_CLASIFICADO,
    estado_validacion: EstadoValidacion | str = EstadoValidacion.LEGACY,
    elegibilidad: ElegibilidadEvidencia | str = ElegibilidadEvidencia.PUNTUABLE,
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
        id_dato_primario=id_dato_primario,
        naturaleza=naturaleza,
        estado_validacion=estado_validacion,
        elegibilidad=elegibilidad,
    )


def evidencias_desde_hallazgos(
    hallazgos,
    *,
    fuente: FuenteEvidencia | str,
    origen: str,
    derivada_de: str | None = None,
    id_dato_primario: str | None = None,
    naturaleza: NaturalezaEvidencia | str = NaturalezaEvidencia.LEGACY_NO_CLASIFICADO,
    estado_validacion: EstadoValidacion | str = EstadoValidacion.LEGACY,
    elegibilidad: ElegibilidadEvidencia | str = ElegibilidadEvidencia.PUNTUABLE,
) -> list[EvidenciaClinica]:
    """Adaptador temporal para listas estructuradas de la aplicación."""
    return [
        evidencia_estructurada(
            hallazgo,
            fuente=fuente,
            origen=origen,
            derivada_de=derivada_de,
            id_dato_primario=id_dato_primario,
            naturaleza=naturaleza,
            estado_validacion=estado_validacion,
            elegibilidad=elegibilidad,
        )
        for hallazgo in (hallazgos or [])
        if str(hallazgo).strip()
    ]


def evidencias_desde_eva(
    valor,
    *,
    valorado: bool,
    origen: str = "eva",
    id_dato_primario: str = "eva_dolor",
) -> list[EvidenciaClinica]:
    """Conserva una sola fuente EVA sin inferir cualidad ni diagnóstico."""
    if not valorado or valor is None:
        return []
    evidencias = [evidencia_estructurada(
        "escala visual analógica del dolor",
        texto_original=f"EVA {valor}/10",
        fuente=FuenteEvidencia.MEDIDO,
        origen=origen,
        id_dato_primario=id_dato_primario,
        naturaleza=NaturalezaEvidencia.DATO_PRIMARIO_MEDIDO,
        estado_validacion=EstadoValidacion.VALIDADO,
        elegibilidad=ElegibilidadEvidencia.NO_PUNTUABLE,
    )]
    if valor >= 4:
        evidencias.append(evidencia_estructurada(
            "dolor",
            texto_original=f"EVA {valor}/10",
            fuente=FuenteEvidencia.REFERIDO_ESTRUCTURADO,
            origen=origen,
            id_dato_primario=id_dato_primario,
            naturaleza=NaturalezaEvidencia.DATO_PRIMARIO_REFERIDO,
            estado_validacion=EstadoValidacion.VALIDADO,
            elegibilidad=ElegibilidadEvidencia.PUNTUABLE,
        ))
    if valor >= 7:
        evidencias.append(evidencia_estructurada(
            "dolor intenso",
            fuente=FuenteEvidencia.INFERIDO,
            origen="clasificacion_eva",
            derivada_de=id_dato_primario,
            id_dato_primario=id_dato_primario,
            naturaleza=NaturalezaEvidencia.INTERPRETACION,
            estado_validacion=EstadoValidacion.PENDIENTE_VALIDACION,
            elegibilidad=ElegibilidadEvidencia.NO_PUNTUABLE,
        ))
    return evidencias
