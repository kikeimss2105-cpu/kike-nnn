from __future__ import annotations

from pathlib import Path

from engine.tanner.interpreting import RespuestaClienteLLM
from engine.tanner.servicio import (
    ejecutar_interpreting_desde_caso,
    ejecutar_noticing_desde_caso,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CASO_OBSTETRICO = REPO_ROOT / "data" / "casos" / "OBS-HTA-001.yaml"


class _ClienteStub:
    """Cliente simulado — mismo patrón que test_retroalimentacion_interpreting.py."""

    def __init__(self, respuesta: RespuestaClienteLLM) -> None:
        self._respuesta = respuesta

    def identificar_conceptos_y_relaciones(self, texto, conceptos_minimos, relaciones_esperadas):
        return self._respuesta


def test_ejecuta_noticing_desde_el_yaml() -> None:
    ejecucion = ejecutar_noticing_desde_caso(
        CASO_OBSTETRICO,
        [
            "pa_165_115",
            "cefalea_intensa",
            "alteracion_visual",
            "gestacion_36",
        ],
    )

    assert ejecucion.caso.id == "OBS-HTA-001"
    assert ejecucion.resultado.completo_sin_errores is True


def test_detecta_omision_critica_desde_servicio() -> None:
    ejecucion = ejecutar_noticing_desde_caso(
        CASO_OBSTETRICO,
        [
            "alteracion_visual",
            "gestacion_36",
        ],
    )

    assert ejecucion.resultado.omisiones_criticas == (
        "pa_165_115",
        "cefalea_intensa",
    )


def test_detecta_seleccion_no_prioritaria_desde_servicio() -> None:
    ejecucion = ejecutar_noticing_desde_caso(
        CASO_OBSTETRICO,
        [
            "pa_165_115",
            "cefalea_intensa",
            "alteracion_visual",
            "gestacion_36",
            "fr_20",
            "pregunta_pareja",
        ],
    )

    assert ejecucion.resultado.seleccionados_no_prioritarios == (
        "fr_20",
        "pregunta_pareja",
    )
    assert ejecucion.resultado.completo_sin_errores is False


def test_conserva_datos_del_caso_en_la_ejecucion() -> None:
    ejecucion = ejecutar_noticing_desde_caso(
        CASO_OBSTETRICO,
        [],
    )

    assert ejecucion.caso.uso_clinico_real is False
    assert "165/115" in ejecucion.caso.escena_inicial
    assert len(ejecucion.caso.indicios_noticing) == 8


def test_ejecuta_interpreting_desde_el_yaml() -> None:
    caso_dummy = ejecutar_noticing_desde_caso(CASO_OBSTETRICO, []).caso
    respuesta = RespuestaClienteLLM(
        conceptos_detectados=caso_dummy.conceptos_minimos_interpreting,
        relaciones_detectadas=caso_dummy.relaciones_esperadas_interpreting,
        exitosa=True,
    )

    ejecucion = ejecutar_interpreting_desde_caso(
        CASO_OBSTETRICO,
        "texto del estudiante",
        cliente=_ClienteStub(respuesta),
    )

    assert ejecucion.caso.id == "OBS-HTA-001"
    assert ejecucion.resultado.completo_sin_errores is True


def test_interpreting_desde_servicio_propaga_fallo_tecnico() -> None:
    ejecucion = ejecutar_interpreting_desde_caso(
        CASO_OBSTETRICO,
        "texto del estudiante",
        cliente=_ClienteStub(
            RespuestaClienteLLM((), (), exitosa=False, detalle_error="Timeout de red")
        ),
    )

    assert ejecucion.resultado.evaluacion_confiable is False
    assert "Timeout de red" in ejecucion.resultado.detalle_error
