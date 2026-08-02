"""Pruebas de evaluar_interpreting usando un cliente simulado (stub).

Estas pruebas verifican la LÓGICA (filtrado, manejo de errores, listas
vacías) sin llamar a ninguna API real. Las pruebas contra el modelo real
de NVIDIA se corren aparte, manualmente, con scripts/probar_interpreting.py
— porque dependen de una clave de API y no son deterministas."""
from __future__ import annotations

from engine.tanner.interpreting import (
    ClienteInterpretacion,
    RespuestaClienteLLM,
    evaluar_interpreting,
)


class _ClienteStub:
    """Cliente simulado: devuelve una respuesta fija, sin red."""

    def __init__(self, respuesta: RespuestaClienteLLM) -> None:
        self._respuesta = respuesta

    def identificar_conceptos_y_relaciones(self, texto, conceptos_minimos, relaciones_esperadas):
        return self._respuesta


CONCEPTOS = ("hipertension_grave", "contexto_obstetrico", "riesgo_de_deterioro_materno")
RELACIONES = ("hipertension_grave_con_manifestaciones_neurologicas",)


def test_texto_vacio_no_llama_al_cliente_y_marca_todo_omitido():
    resultado = evaluar_interpreting(
        CONCEPTOS, RELACIONES, "", cliente=_ClienteStub(
            RespuestaClienteLLM((), (), exitosa=True)
        )
    )
    assert resultado.evaluacion_confiable is True
    assert resultado.conceptos_reconocidos == ()
    assert resultado.conceptos_omitidos == CONCEPTOS


def test_reconoce_conceptos_y_relaciones_detectadas_por_el_cliente():
    stub = _ClienteStub(RespuestaClienteLLM(
        conceptos_detectados=("hipertension_grave", "contexto_obstetrico"),
        relaciones_detectadas=("hipertension_grave_con_manifestaciones_neurologicas",),
        exitosa=True,
    ))
    resultado = evaluar_interpreting(
        CONCEPTOS, RELACIONES,
        "La paciente tiene presión muy alta y está embarazada, con síntomas neurológicos.",
        cliente=stub,
    )
    assert resultado.conceptos_reconocidos == ("hipertension_grave", "contexto_obstetrico")
    assert resultado.conceptos_omitidos == ("riesgo_de_deterioro_materno",)
    assert resultado.relaciones_reconocidas == RELACIONES
    assert resultado.relaciones_omitidas == ()
    assert resultado.completo_sin_errores is False  # faltó un concepto


def test_completo_sin_errores_cuando_reconoce_todo():
    stub = _ClienteStub(RespuestaClienteLLM(
        conceptos_detectados=CONCEPTOS,
        relaciones_detectadas=RELACIONES,
        exitosa=True,
    ))
    resultado = evaluar_interpreting(CONCEPTOS, RELACIONES, "texto completo", cliente=stub)
    assert resultado.completo_sin_errores is True


def test_filtra_detecciones_fuera_del_catalogo_esperado():
    """Seguridad: si el cliente 'alucina' un concepto que no estaba en la
    lista permitida, se descarta — nunca se acepta a ciegas."""
    stub = _ClienteStub(RespuestaClienteLLM(
        conceptos_detectados=("hipertension_grave", "concepto_inventado_que_no_deberia_existir"),
        relaciones_detectadas=(),
        exitosa=True,
    ))
    resultado = evaluar_interpreting(CONCEPTOS, RELACIONES, "texto", cliente=stub)
    assert resultado.conceptos_reconocidos == ("hipertension_grave",)
    assert "concepto_inventado_que_no_deberia_existir" not in resultado.conceptos_reconocidos


def test_cliente_fallido_marca_evaluacion_no_confiable_sin_asumir_nada():
    stub = _ClienteStub(RespuestaClienteLLM(
        (), (), exitosa=False, detalle_error="Timeout de red"
    ))
    resultado = evaluar_interpreting(CONCEPTOS, RELACIONES, "texto real", cliente=stub)
    assert resultado.evaluacion_confiable is False
    assert resultado.detalle_error == "Timeout de red"
    assert resultado.conceptos_reconocidos == ()  # no se inventa un resultado positivo
