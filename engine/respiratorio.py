"""Contrato estructural único para frecuencia respiratoria.

Los rangos son exclusivamente los heredados de ``interpretaciones.py``.
Permanecen pendientes de validación clínica y, por ello, sus derivaciones no
son puntuables. Este módulo no diagnostica ni infiere signos no observados.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from engine.evidencia import (
    ElegibilidadEvidencia,
    EstadoValidacion,
    EvidenciaClinica,
    FuenteEvidencia,
    NaturalezaEvidencia,
    evidencia_estructurada,
)


class ClasificacionFR(str, Enum):
    BRADIPNEA = "BRADIPNEA"
    DENTRO_DE_RANGO = "DENTRO_DE_RANGO"
    VIGILANCIA = "VIGILANCIA"
    TAQUIPNEA = "TAQUIPNEA"
    TAQUIPNEA_MARCADA = "TAQUIPNEA_MARCADA"


@dataclass(frozen=True)
class AlertaFR:
    nivel: str
    mensaje: str
    accion_sugerida: str


@dataclass(frozen=True)
class ReglaFR:
    regla_id: str
    perfil: str
    minimo: float | None
    maximo: float | None
    clasificacion: ClasificacionFR
    interpretacion: str

    def aplica(self, valor_rpm: float) -> bool:
        return (
            (self.minimo is None or valor_rpm >= self.minimo)
            and (self.maximo is None or valor_rpm <= self.maximo)
        )


@dataclass(frozen=True)
class ResultadoFR:
    valor_rpm: float | None
    valorado: bool
    perfil: str | None
    edad: float | None
    contexto_obstetrico: Any
    origen: str
    id_dato_primario: str
    clasificacion: ClasificacionFR | None
    interpretacion: str | None
    regla_id: str | None
    estado_validacion: EstadoValidacion
    terminos_derivados: tuple[str, ...]
    alerta: AlertaFR | None
    error: str | None = None


_REGLAS = (
    ReglaFR("FR_ADULTO_MENOR_12", "Adulto", None, 11, ClasificacionFR.BRADIPNEA, "Bradipnea"),
    ReglaFR("FR_ADULTO_12_20", "Adulto", 12, 20, ClasificacionFR.DENTRO_DE_RANGO, "Frecuencia respiratoria dentro de rango adulto esperado"),
    ReglaFR("FR_ADULTO_21_30", "Adulto", 21, 30, ClasificacionFR.TAQUIPNEA, "Taquipnea"),
    ReglaFR("FR_ADULTO_MAYOR_30", "Adulto", 31, None, ClasificacionFR.TAQUIPNEA_MARCADA, "Taquipnea marcada"),
    ReglaFR("FR_GERIATRICO_MENOR_12", "Geriátrico", None, 11, ClasificacionFR.BRADIPNEA, "Bradipnea"),
    ReglaFR("FR_GERIATRICO_12_20", "Geriátrico", 12, 20, ClasificacionFR.DENTRO_DE_RANGO, "FR dentro de rango esperado en adulto mayor"),
    ReglaFR("FR_GERIATRICO_21_28", "Geriátrico", 21, 28, ClasificacionFR.TAQUIPNEA, "Taquipnea en adulto mayor"),
    ReglaFR("FR_GERIATRICO_MAYOR_28", "Geriátrico", 29, None, ClasificacionFR.TAQUIPNEA_MARCADA, "Taquipnea marcada en adulto mayor"),
    ReglaFR("FR_PEDIATRICO_MENOR_20", "Pediátrico", None, 19, ClasificacionFR.VIGILANCIA, "FR baja o en vigilancia para paciente pediátrico"),
    ReglaFR("FR_PEDIATRICO_20_30", "Pediátrico", 20, 30, ClasificacionFR.DENTRO_DE_RANGO, "Frecuencia respiratoria dentro de rango pediátrico general"),
    ReglaFR("FR_PEDIATRICO_31_40", "Pediátrico", 31, 40, ClasificacionFR.TAQUIPNEA, "Taquipnea pediátrica"),
    ReglaFR("FR_PEDIATRICO_MAYOR_40", "Pediátrico", 41, None, ClasificacionFR.TAQUIPNEA_MARCADA, "Taquipnea pediátrica marcada"),
    ReglaFR("FR_NEONATAL_MENOR_30", "Recién nacido", None, 29, ClasificacionFR.BRADIPNEA, "Bradipnea para recién nacido"),
    ReglaFR("FR_NEONATAL_30_60", "Recién nacido", 30, 60, ClasificacionFR.DENTRO_DE_RANGO, "Frecuencia respiratoria dentro de rango esperado para recién nacido"),
    ReglaFR("FR_NEONATAL_MAYOR_60", "Recién nacido", 61, None, ClasificacionFR.TAQUIPNEA, "Taquipnea en recién nacido"),
    ReglaFR("FR_OBSTETRICO_MENOR_12", "Obstétrico", None, 11, ClasificacionFR.BRADIPNEA, "Bradipnea"),
    ReglaFR("FR_OBSTETRICO_12_20", "Obstétrico", 12, 20, ClasificacionFR.DENTRO_DE_RANGO, "FR dentro de rango adulto esperado en obstetricia"),
    ReglaFR("FR_OBSTETRICO_21_24", "Obstétrico", 21, 24, ClasificacionFR.VIGILANCIA, "FR en vigilancia obstétrica"),
    ReglaFR("FR_OBSTETRICO_MAYOR_24", "Obstétrico", 25, None, ClasificacionFR.TAQUIPNEA, "Taquipnea: valorar signos de alarma obstétrica"),
    ReglaFR("FR_LEGACY_MENOR_12", "LEGACY_GENERAL", None, 11, ClasificacionFR.BRADIPNEA, "Bradipnea"),
    ReglaFR("FR_LEGACY_12_20", "LEGACY_GENERAL", 12, 20, ClasificacionFR.DENTRO_DE_RANGO, "Frecuencia respiratoria dentro de rango adulto esperado"),
    ReglaFR("FR_LEGACY_21_30", "LEGACY_GENERAL", 21, 30, ClasificacionFR.TAQUIPNEA, "Taquipnea"),
    ReglaFR("FR_LEGACY_MAYOR_30", "LEGACY_GENERAL", 31, None, ClasificacionFR.TAQUIPNEA_MARCADA, "Taquipnea marcada"),
)


def _terminos_derivados(clasificacion: ClasificacionFR) -> tuple[str, ...]:
    if clasificacion == ClasificacionFR.BRADIPNEA:
        return ("bradipnea",)
    if clasificacion in {ClasificacionFR.TAQUIPNEA, ClasificacionFR.TAQUIPNEA_MARCADA}:
        return ("taquipnea",)
    return ()


def _alerta_desde_clasificacion(valor_rpm: float, clasificacion: ClasificacionFR) -> AlertaFR | None:
    if clasificacion == ClasificacionFR.TAQUIPNEA_MARCADA:
        return AlertaFR(
            "Alta",
            f"FR {valor_rpm:g} rpm: taquipnea marcada.",
            "Valorar trabajo respiratorio y signos observados de deterioro.",
        )
    if clasificacion == ClasificacionFR.TAQUIPNEA:
        return AlertaFR(
            "Media",
            f"FR {valor_rpm:g} rpm: taquipnea.",
            "Vigilar patrón respiratorio, disnea y evolución clínica.",
        )
    return None


def evaluar_fr(
    valor_rpm,
    *,
    valorado: bool,
    perfil: str | None,
    edad=None,
    contexto_obstetrico=None,
    origen: str = "respiratorio.fr",
    id_dato_primario: str = "fr",
) -> ResultadoFR:
    """Evalúa FR una sola vez, sin fallback de población ni signos inferidos."""
    valor = valor_rpm if valorado else None
    base = dict(
        valor_rpm=valor,
        valorado=bool(valorado),
        perfil=perfil,
        edad=edad,
        contexto_obstetrico=contexto_obstetrico,
        origen=origen,
        id_dato_primario=id_dato_primario,
        estado_validacion=(
            EstadoValidacion.LEGACY
            if perfil == "LEGACY_GENERAL"
            else EstadoValidacion.PENDIENTE_VALIDACION
        ),
    )
    if not valorado:
        return ResultadoFR(
            **base, clasificacion=None, interpretacion=None, regla_id=None,
            terminos_derivados=(), alerta=None,
        )
    if valor is None:
        return ResultadoFR(
            **base, clasificacion=None, interpretacion=None, regla_id=None,
            terminos_derivados=(), alerta=None, error="FR valorada sin valor numérico.",
        )
    reglas_perfil = tuple(regla for regla in _REGLAS if regla.perfil == perfil)
    if not reglas_perfil:
        return ResultadoFR(
            **base, clasificacion=None, interpretacion=None, regla_id=None,
            terminos_derivados=(), alerta=None, error="Perfil respiratorio no reconocido.",
        )
    regla = next((candidata for candidata in reglas_perfil if candidata.aplica(valor)), None)
    if regla is None:
        return ResultadoFR(
            **base, clasificacion=None, interpretacion=None, regla_id=None,
            terminos_derivados=(), alerta=None, error="FR fuera del contrato implementado.",
        )
    return ResultadoFR(
        **base,
        clasificacion=regla.clasificacion,
        interpretacion=regla.interpretacion,
        regla_id=regla.regla_id,
        terminos_derivados=_terminos_derivados(regla.clasificacion),
        alerta=_alerta_desde_clasificacion(valor, regla.clasificacion),
    )


def evaluar_fr_legacy_alertas(valor_rpm, *, id_dato_primario: str = "fr_legacy") -> ResultadoFR:
    """Compatibilidad de la API histórica de alertas; un único propietario."""
    return evaluar_fr(
        valor_rpm,
        valorado=valor_rpm is not None,
        perfil="LEGACY_GENERAL",
        origen="api_legacy_alertas",
        id_dato_primario=id_dato_primario,
    )


def evidencias_desde_resultado_fr(resultado: ResultadoFR) -> list[EvidenciaClinica]:
    if not resultado.valorado or resultado.valor_rpm is None:
        return []
    evidencias = [evidencia_estructurada(
        "frecuencia respiratoria",
        texto_original=f"{resultado.valor_rpm:g} rpm",
        fuente=FuenteEvidencia.MEDIDO,
        origen=resultado.origen,
        id_dato_primario=resultado.id_dato_primario,
        naturaleza=NaturalezaEvidencia.DATO_PRIMARIO_MEDIDO,
        estado_validacion=EstadoValidacion.VALIDADO,
        elegibilidad=ElegibilidadEvidencia.NO_PUNTUABLE,
    )]
    evidencias.extend(
        evidencia_estructurada(
            termino,
            fuente=FuenteEvidencia.INFERIDO,
            origen="clasificacion_fr",
            derivada_de=resultado.id_dato_primario,
            id_dato_primario=resultado.id_dato_primario,
            naturaleza=NaturalezaEvidencia.DERIVACION_DETERMINISTA,
            estado_validacion=resultado.estado_validacion,
            elegibilidad=ElegibilidadEvidencia.NO_PUNTUABLE,
        )
        for termino in resultado.terminos_derivados
    )
    return evidencias


def evidencias_desde_spo2(
    valor,
    *,
    valorado: bool,
    origen: str = "respiratorio.spo2",
    id_dato_primario: str = "spo2",
) -> list[EvidenciaClinica]:
    """Conserva SpO2 y solo su clasificación semántica, nunca cianosis."""
    if not valorado or valor is None:
        return []
    evidencias = [evidencia_estructurada(
        "saturación de oxígeno",
        texto_original=f"{valor}%",
        fuente=FuenteEvidencia.MEDIDO,
        origen=origen,
        id_dato_primario=id_dato_primario,
        naturaleza=NaturalezaEvidencia.DATO_PRIMARIO_MEDIDO,
        estado_validacion=EstadoValidacion.VALIDADO,
        elegibilidad=ElegibilidadEvidencia.NO_PUNTUABLE,
    )]
    if valor <= 95:
        evidencias.append(evidencia_estructurada(
            "saturación baja",
            fuente=FuenteEvidencia.INFERIDO,
            origen="clasificacion_spo2",
            derivada_de=id_dato_primario,
            id_dato_primario=id_dato_primario,
            naturaleza=NaturalezaEvidencia.DERIVACION_DETERMINISTA,
            estado_validacion=EstadoValidacion.PENDIENTE_VALIDACION,
            elegibilidad=ElegibilidadEvidencia.NO_PUNTUABLE,
        ))
    return evidencias
