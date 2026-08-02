from __future__ import annotations

from pathlib import Path

from engine.tanner.casos import cargar_caso_tanner
from engine.tanner.interpreting import RespuestaClienteLLM, evaluar_interpreting
from engine.tanner.retroalimentacion_interpreting import (
    generar_retroalimentacion_interpreting,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CASO_OBSTETRICO = REPO_ROOT / "data" / "casos" / "OBS-HTA-001.yaml"


class _ClienteStub:
    def __init__(self, respuesta: RespuestaClienteLLM) -> None:
        self._respuesta = respuesta

    def identificar_conceptos_y_relaciones(self, texto, conceptos_minimos, relaciones_esperadas):
        return self._respuesta


def _evaluar(texto: str, respuesta: RespuestaClienteLLM):
    caso = cargar_caso_tanner(CASO_OBSTETRICO)
    resultado = evaluar_interpreting(
        caso.conceptos_minimos_interpreting,
        caso.relaciones_esperadas_interpreting,
        texto,
        cliente=_ClienteStub(respuesta),
    )
    return caso, resultado


def test_caso_real_expone_conceptos_y_relaciones_de_interpreting() -> None:
    caso = cargar_caso_tanner(CASO_OBSTETRICO)

    assert caso.conceptos_minimos_interpreting == (
        "hipertension_grave",
        "contexto_obstetrico",
        "sintomas_neurologicos_relevantes",
        "riesgo_de_deterioro_materno",
        "necesidad_de_evaluacion_y_atencion_urgente",
    )
    assert caso.relaciones_esperadas_interpreting == (
        "hipertension_grave_con_manifestaciones_neurologicas",
        "embarazo_con_hipertension_grave_requiere_evaluacion_de_trastorno_hipertensivo",
        "signos_de_alarma_con_necesidad_de_escalamiento",
    )


def test_resumen_con_totales_reales() -> None:
    caso, resultado = _evaluar(
        "La paciente tiene hipertensión grave y está embarazada.",
        RespuestaClienteLLM(
            conceptos_detectados=("hipertension_grave", "contexto_obstetrico"),
            relaciones_detectadas=(),
            exitosa=True,
        ),
    )

    retro = generar_retroalimentacion_interpreting(caso, resultado, "texto")

    assert retro.resumen == "Se reconocieron 2 de 5 conceptos y 0 de 3 relaciones esperadas."


def test_humaniza_conceptos_omitidos() -> None:
    caso, resultado = _evaluar(
        "texto",
        RespuestaClienteLLM(conceptos_detectados=(), relaciones_detectadas=(), exitosa=True),
    )

    retro = generar_retroalimentacion_interpreting(caso, resultado, "texto")

    assert "Riesgo de deterioro materno" in retro.conceptos_omitidos
    assert "Contexto obstetrico" in retro.conceptos_omitidos


def test_texto_vacio_da_mensaje_distinto_a_omision() -> None:
    caso, resultado = _evaluar(
        "",
        RespuestaClienteLLM(conceptos_detectados=(), relaciones_detectadas=(), exitosa=True),
    )

    retro = generar_retroalimentacion_interpreting(caso, resultado, "")

    assert retro.resumen == "No se recibió texto de interpretación."
    assert retro.prioridad_revision == "Escribe tu interpretación de la escena antes de continuar."
    assert retro.advertencias == ()


def test_fallo_de_evaluacion_no_se_confunde_con_omision_del_estudiante() -> None:
    caso, resultado = _evaluar(
        "texto real",
        RespuestaClienteLLM((), (), exitosa=False, detalle_error="Timeout de red"),
    )

    retro = generar_retroalimentacion_interpreting(caso, resultado, "texto real")

    assert retro.resumen == "La evaluación automática no pudo completarse por un fallo técnico."
    assert len(retro.advertencias) == 1
    assert "Timeout de red" in retro.advertencias[0]
    assert "NO significa que tu interpretación esté incompleta" in retro.advertencias[0]
    assert retro.prioridad_revision == (
        "Hubo un fallo técnico en la evaluación. Vuelve a enviar tu interpretación."
    )
    assert retro.conceptos_reconocidos == ()


def test_retroalimentacion_completa_sin_omisiones() -> None:
    caso = cargar_caso_tanner(CASO_OBSTETRICO)
    caso, resultado = _evaluar(
        "texto completo",
        RespuestaClienteLLM(
            conceptos_detectados=caso.conceptos_minimos_interpreting,
            relaciones_detectadas=caso.relaciones_esperadas_interpreting,
            exitosa=True,
        ),
    )

    retro = generar_retroalimentacion_interpreting(caso, resultado, "texto completo")

    assert retro.conceptos_omitidos == ()
    assert retro.relaciones_omitidas == ()
    assert retro.prioridad_revision == (
        "Tu interpretación reconoce todos los conceptos y relaciones esperados."
    )


def test_como_texto_conserva_secciones_relevantes() -> None:
    caso, resultado = _evaluar(
        "texto",
        RespuestaClienteLLM(
            conceptos_detectados=("hipertension_grave",),
            relaciones_detectadas=(),
            exitosa=True,
        ),
    )

    retro = generar_retroalimentacion_interpreting(caso, resultado, "texto")
    texto = retro.como_texto()

    assert "Conceptos reconocidos:" in texto
    assert "Conceptos no reflejados:" in texto
    assert "Relaciones no reflejadas:" in texto
    assert "Prioridad de revisión:" in texto
