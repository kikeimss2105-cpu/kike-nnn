"""Contrato tipado y fail-closed para la Escala de Coma de Glasgow.

Glasgow conserva observaciones de respuesta; no genera hallazgos NANDA.
La genealogía del total vive en ``ResultadoGlasgow`` para no ampliar todavía
el contrato global de ``EvidenciaClinica``.
"""

from dataclasses import dataclass
from uuid import uuid4

from engine.evidencia import (
    ElegibilidadEvidencia,
    EstadoValidacion,
    EvidenciaClinica,
    FuenteEvidencia,
    NaturalezaEvidencia,
    evidencia_estructurada,
)


OPCIONES_OCULAR = {
    1: "No abre",
    2: "Al dolor",
    3: "A la voz",
    4: "Espontánea",
}
OPCIONES_VERBAL = {
    1: "Sin respuesta",
    2: "Sonidos incomprensibles",
    3: "Palabras inapropiadas",
    4: "Confuso",
    5: "Orientado",
}
OPCIONES_MOTORA = {
    1: "Sin respuesta",
    2: "Extensión anormal",
    3: "Flexión anormal",
    4: "Retira al dolor",
    5: "Localiza dolor",
    6: "Obedece órdenes",
}


@dataclass(frozen=True)
class ComponenteGlasgow:
    nombre: str
    valor: int
    etiqueta: str
    id_dato_primario: str
    evidencia: EvidenciaClinica


@dataclass(frozen=True)
class ResultadoGlasgow:
    valorado: bool
    id_valoracion: str | None
    ocular: ComponenteGlasgow | None
    verbal: ComponenteGlasgow | None
    motora: ComponenteGlasgow | None
    total: int | None
    ids_progenitores_total: tuple[str, ...]
    evidencia_total: EvidenciaClinica | None
    interpretacion: str | None
    evidencia_interpretacion: EvidenciaClinica | None
    evidencias: tuple[EvidenciaClinica, ...]
    error: str | None = None


def nuevo_id_valoracion() -> str:
    return f"glasgow-{uuid4()}"


def resolver_id_valoracion(
    *,
    valorado_actual: bool,
    valorado_previo: bool,
    id_actual: str | None,
) -> str | None:
    """Mantiene el episodio activo y crea otro tras desactivar/reactivar."""
    if not valorado_actual:
        return None
    if not valorado_previo or not id_actual:
        return nuevo_id_valoracion()
    return id_actual


def interpretar_total_glasgow(total: int) -> str:
    """Clasificación heredada, aislada como interpretación no puntuable."""
    if total <= 8:
        return "Compromiso neurológico grave"
    if total <= 12:
        return "Compromiso neurológico moderado"
    if total <= 14:
        return "Compromiso neurológico leve"
    return "Estado neurológico aparentemente conservado"


def _no_valorado(error: str | None = None) -> ResultadoGlasgow:
    return ResultadoGlasgow(
        valorado=False,
        id_valoracion=None,
        ocular=None,
        verbal=None,
        motora=None,
        total=None,
        ids_progenitores_total=(),
        evidencia_total=None,
        interpretacion=None,
        evidencia_interpretacion=None,
        evidencias=(),
        error=error,
    )


def _componente(
    nombre: str,
    valor: int,
    opciones: dict[int, str],
    id_valoracion: str,
) -> ComponenteGlasgow:
    etiqueta = opciones[valor]
    id_primario = f"{id_valoracion}:{nombre}"
    evidencia = evidencia_estructurada(
        f"respuesta {nombre} Glasgow",
        texto_original=f"Glasgow {nombre}: {valor} - {etiqueta}",
        fuente=FuenteEvidencia.OBSERVADO,
        origen=f"glasgow.{nombre}",
        id_dato_primario=id_primario,
        naturaleza=NaturalezaEvidencia.DATO_PRIMARIO_OBSERVADO,
        estado_validacion=EstadoValidacion.VALIDADO,
        elegibilidad=ElegibilidadEvidencia.NO_PUNTUABLE,
    )
    return ComponenteGlasgow(nombre, valor, etiqueta, id_primario, evidencia)


def evaluar_glasgow(
    ocular: int | None,
    verbal: int | None,
    motora: int | None,
    *,
    valorado: bool,
    id_valoracion: str | None = None,
) -> ResultadoGlasgow:
    """Valida componentes y calcula el total sin fabricar hallazgos clínicos."""
    if not valorado:
        return _no_valorado()

    valores_validos = (
        type(ocular) is int and ocular in OPCIONES_OCULAR,
        type(verbal) is int and verbal in OPCIONES_VERBAL,
        type(motora) is int and motora in OPCIONES_MOTORA,
    )
    if not all(valores_validos):
        return _no_valorado("Componentes Glasgow ausentes o fuera de rango.")

    episodio = str(id_valoracion or nuevo_id_valoracion()).strip()
    if not episodio:
        return _no_valorado("La valoración Glasgow requiere identidad de episodio.")

    componente_ocular = _componente("ocular", ocular, OPCIONES_OCULAR, episodio)
    componente_verbal = _componente("verbal", verbal, OPCIONES_VERBAL, episodio)
    componente_motora = _componente("motora", motora, OPCIONES_MOTORA, episodio)
    progenitores = (
        componente_ocular.id_dato_primario,
        componente_verbal.id_dato_primario,
        componente_motora.id_dato_primario,
    )
    total = ocular + verbal + motora
    evidencia_total = evidencia_estructurada(
        "total Glasgow",
        texto_original=f"Glasgow {total}/15 (O{ocular}, V{verbal}, M{motora})",
        fuente=FuenteEvidencia.INFERIDO,
        origen="glasgow.total",
        derivada_de=episodio,
        naturaleza=NaturalezaEvidencia.DERIVACION_DETERMINISTA,
        estado_validacion=EstadoValidacion.VALIDADO,
        elegibilidad=ElegibilidadEvidencia.NO_PUNTUABLE,
    )
    interpretacion = interpretar_total_glasgow(total)
    evidencia_interpretacion = evidencia_estructurada(
        interpretacion,
        texto_original=f"Interpretación de Glasgow {total}/15: {interpretacion}",
        fuente=FuenteEvidencia.INFERIDO,
        origen="glasgow.interpretacion",
        derivada_de=episodio,
        naturaleza=NaturalezaEvidencia.INTERPRETACION,
        estado_validacion=EstadoValidacion.VALIDADO,
        elegibilidad=ElegibilidadEvidencia.NO_PUNTUABLE,
    )
    evidencias = (
        componente_ocular.evidencia,
        componente_verbal.evidencia,
        componente_motora.evidencia,
        evidencia_total,
        evidencia_interpretacion,
    )
    return ResultadoGlasgow(
        valorado=True,
        id_valoracion=episodio,
        ocular=componente_ocular,
        verbal=componente_verbal,
        motora=componente_motora,
        total=total,
        ids_progenitores_total=progenitores,
        evidencia_total=evidencia_total,
        interpretacion=interpretacion,
        evidencia_interpretacion=evidencia_interpretacion,
        evidencias=evidencias,
    )


def alertas_desde_glasgow(resultado: ResultadoGlasgow) -> list[dict[str, str]]:
    """Produce alertas educativas sin inferir reflejos ni función no observada."""
    if not resultado.valorado or resultado.total is None:
        return []
    if resultado.total <= 8:
        return [{
            "Nivel": "Alta",
            "Área": "Neurológico",
            "Origen": "glasgow",
            "Alerta": f"Glasgow {resultado.total}/15: compromiso neurológico grave.",
            "Acción sugerida": "Realizar valoración neurológica seriada y actuar según protocolo institucional.",
        }]
    if resultado.total <= 12:
        return [{
            "Nivel": "Media",
            "Área": "Neurológico",
            "Origen": "glasgow",
            "Alerta": f"Glasgow {resultado.total}/15: compromiso neurológico moderado.",
            "Acción sugerida": "Realizar valoración neurológica seriada y actuar según protocolo institucional.",
        }]
    return []


def sincronizar_alertas_glasgow(
    alertas: list[dict],
    resultado: ResultadoGlasgow,
) -> list[dict]:
    """Reemplaza solo alertas derivadas de Glasgow por las del estado actual."""
    ajenas = [
        alerta for alerta in (alertas or [])
        if not (
            alerta.get("Origen") == "glasgow"
            or (
                alerta.get("Área") == "Neurológico"
                and str(alerta.get("Alerta", "")).startswith("Glasgow ")
            )
        )
    ]
    return ajenas + alertas_desde_glasgow(resultado)


def actualizar_datos_paciente_glasgow(
    datos_paciente: dict,
    resultado: ResultadoGlasgow,
) -> dict:
    """Actualiza únicamente los campos exportables dependientes de Glasgow."""
    actualizados = dict(datos_paciente or {})
    if not resultado.valorado:
        valores = {
            "Glasgow valoración ID": "No valorado",
            "Glasgow ocular": "No valorado",
            "Glasgow verbal": "No valorado",
            "Glasgow motora": "No valorado",
            "Glasgow total": "No valorado",
            "Interpretación Glasgow": "No valorado",
        }
    else:
        valores = {
            "Glasgow valoración ID": resultado.id_valoracion,
            "Glasgow ocular": f"{resultado.ocular.valor} - {resultado.ocular.etiqueta}",
            "Glasgow verbal": f"{resultado.verbal.valor} - {resultado.verbal.etiqueta}",
            "Glasgow motora": f"{resultado.motora.valor} - {resultado.motora.etiqueta}",
            "Glasgow total": resultado.total,
            "Interpretación Glasgow": resultado.interpretacion,
        }
    actualizados.update(valores)
    return actualizados
