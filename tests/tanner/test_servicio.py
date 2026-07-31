from __future__ import annotations

from pathlib import Path

from engine.tanner.servicio import ejecutar_noticing_desde_caso


REPO_ROOT = Path(__file__).resolve().parents[2]
CASO_OBSTETRICO = REPO_ROOT / "data" / "casos" / "OBS-HTA-001.yaml"


def test_ejecuta_noticing_desde_el_yaml() -> None:
    ejecucion = ejecutar_noticing_desde_caso(
        CASO_OBSTETRICO,
        [
            "pa_165_115",
            "cefalea_intensa",
            "fotofobia",
            "gestacion_36",
            "inquietud",
        ],
    )

    assert ejecucion.caso.id == "OBS-HTA-001"
    assert ejecucion.resultado.completo_sin_errores is True


def test_detecta_omision_critica_desde_servicio() -> None:
    ejecucion = ejecutar_noticing_desde_caso(
        CASO_OBSTETRICO,
        [
            "fotofobia",
            "gestacion_36",
            "inquietud",
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
            "fotofobia",
            "gestacion_36",
            "inquietud",
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
