"""Retroalimentación determinista para la fase Interpreting.

La EVALUACIÓN de Interpreting usa un LLM (ver interpreting.py) porque
requiere comprensión semántica de texto libre. La RETROALIMENTACIÓN que
se le muestra al estudiante, en cambio, es 100% determinista: se
construye únicamente a partir del catálogo de conceptos/relaciones ya
definido en el YAML del caso y del resultado ya filtrado por
evaluar_interpreting — nunca a partir de una redacción libre del LLM.
Esto mantiene la misma garantía que Noticing: la retroalimentación es
auditable y reproducible, no una opinión generada en el momento.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine.tanner.casos import CasoTanner
from engine.tanner.interpreting import ResultadoInterpreting


@dataclass(frozen=True, slots=True)
class RetroalimentacionInterpreting:
    """Retroalimentación estructurada y auditable de Interpreting."""

    resumen: str
    conceptos_reconocidos: tuple[str, ...]
    conceptos_omitidos: tuple[str, ...]
    relaciones_reconocidas: tuple[str, ...]
    relaciones_omitidas: tuple[str, ...]
    advertencias: tuple[str, ...]
    prioridad_revision: str

    def como_texto(self) -> str:
        """Devuelve una representación legible sin alterar el contenido."""

        secciones = [self.resumen]

        _agregar_seccion(secciones, "Conceptos reconocidos", self.conceptos_reconocidos)
        _agregar_seccion(secciones, "Conceptos no reflejados", self.conceptos_omitidos)
        _agregar_seccion(secciones, "Relaciones reconocidas", self.relaciones_reconocidas)
        _agregar_seccion(secciones, "Relaciones no reflejadas", self.relaciones_omitidas)
        _agregar_seccion(secciones, "Advertencias", self.advertencias)

        secciones.append(f"Prioridad de revisión:\n{self.prioridad_revision}")

        return "\n\n".join(secciones)


def generar_retroalimentacion_interpreting(
    caso: CasoTanner,
    resultado: ResultadoInterpreting,
    texto_interpretacion: str,
) -> RetroalimentacionInterpreting:
    """Genera retroalimentación únicamente desde el contrato del caso.

    Recibe texto_interpretacion además de resultado (y no solo el
    resultado) porque evaluar_interpreting no distingue, en su forma de
    resultado, entre "el estudiante no escribió nada" y "escribió algo
    que no reconoció ningún concepto" — son situaciones pedagógicamente
    distintas y requieren mensajes distintos.
    """

    conceptos_reconocidos = tuple(_humanizar(c) for c in resultado.conceptos_reconocidos)
    conceptos_omitidos = tuple(_humanizar(c) for c in resultado.conceptos_omitidos)
    relaciones_reconocidas = tuple(_humanizar(r) for r in resultado.relaciones_reconocidas)
    relaciones_omitidas = tuple(_humanizar(r) for r in resultado.relaciones_omitidas)

    texto_vacio = not (texto_interpretacion or "").strip()

    resumen = _construir_resumen(resultado, texto_vacio)
    advertencias = _construir_advertencias(resultado, texto_vacio)
    prioridad_revision = _determinar_prioridad_revision(resultado, texto_vacio)

    return RetroalimentacionInterpreting(
        resumen=resumen,
        conceptos_reconocidos=conceptos_reconocidos,
        conceptos_omitidos=conceptos_omitidos,
        relaciones_reconocidas=relaciones_reconocidas,
        relaciones_omitidas=relaciones_omitidas,
        advertencias=advertencias,
        prioridad_revision=prioridad_revision,
    )


def _construir_resumen(resultado: ResultadoInterpreting, texto_vacio: bool) -> str:
    if texto_vacio:
        return "No se recibió texto de interpretación."

    if not resultado.evaluacion_confiable:
        return "La evaluación automática no pudo completarse por un fallo técnico."

    total_conceptos = len(resultado.conceptos_esperados)
    total_relaciones = len(resultado.relaciones_esperadas)
    reconocidos_conceptos = len(resultado.conceptos_reconocidos)
    reconocidas_relaciones = len(resultado.relaciones_reconocidas)

    return (
        f"Se reconocieron {reconocidos_conceptos} de {total_conceptos} conceptos "
        f"y {reconocidas_relaciones} de {total_relaciones} relaciones esperadas."
    )


def _construir_advertencias(
    resultado: ResultadoInterpreting,
    texto_vacio: bool,
) -> tuple[str, ...]:
    advertencias: list[str] = []

    if not texto_vacio and not resultado.evaluacion_confiable:
        detalle = resultado.detalle_error or "sin detalle disponible"
        advertencias.append(
            "No se generó retroalimentación de contenido porque la evaluación "
            f"automática falló ({detalle}). Esto NO significa que tu "
            "interpretación esté incompleta — vuelve a enviarla."
        )

    return tuple(advertencias)


def _determinar_prioridad_revision(
    resultado: ResultadoInterpreting,
    texto_vacio: bool,
) -> str:
    if texto_vacio:
        return "Escribe tu interpretación de la escena antes de continuar."

    if not resultado.evaluacion_confiable:
        return "Hubo un fallo técnico en la evaluación. Vuelve a enviar tu interpretación."

    if resultado.conceptos_omitidos or resultado.relaciones_omitidas:
        return (
            "Revisa los conceptos y relaciones que tu interpretación no reflejó "
            "todavía."
        )

    return "Tu interpretación reconoce todos los conceptos y relaciones esperados."


def _humanizar(identificador: str) -> str:
    """Convierte una clave técnica del YAML en texto legible.

    Misma lógica que _humanizar_fundamento en retroalimentacion.py — se
    duplica intencionalmente en vez de importarse: son módulos de fases
    distintas y no deben depender uno del otro.
    """

    texto = identificador.replace("_", " ").strip()

    if not texto:
        return texto

    return texto[0].upper() + texto[1:]


def _agregar_seccion(
    secciones: list[str],
    titulo: str,
    elementos: tuple[str, ...],
) -> None:
    if not elementos:
        return

    cuerpo = "\n".join(f"- {elemento}" for elemento in elementos)
    secciones.append(f"{titulo}:\n{cuerpo}")
