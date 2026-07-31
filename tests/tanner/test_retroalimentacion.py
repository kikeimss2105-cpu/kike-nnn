from __future__ import annotations

from pathlib import Path

from engine.tanner import ejecutar_noticing_desde_caso
from engine.tanner.retroalimentacion import (
    generar_retroalimentacion_noticing,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CASO_OBSTETRICO = REPO_ROOT / "data" / "casos" / "OBS-HTA-001.yaml"


def test_genera_resumen_con_totales_reales() -> None:
    ejecucion = ejecutar_noticing_desde_caso(
        CASO_OBSTETRICO,
        ["pa_165_115", "cefalea_intensa"],
    )

    retro = generar_retroalimentacion_noticing(
        ejecucion.caso,
        ejecucion.resultado,
    )

    assert retro.resumen == "Se reconocieron 2 de 5 indicios esperados."


def test_explica_omision_critica_desde_yaml() -> None:
    ejecucion = ejecutar_noticing_desde_caso(
        CASO_OBSTETRICO,
        ["fotofobia", "gestacion_36", "inquietud"],
    )

    retro = generar_retroalimentacion_noticing(
        ejecucion.caso,
        ejecucion.resultado,
    )

    assert retro.omisiones_criticas == (
        (
            "Presion arterial de 165/115 mmHg. "
            "Fundamento: Hipertension grave."
        ),
        (
            "Cefalea intensa. "
            "Fundamento: Manifestacion neurologica de alarma."
        ),
    )
    assert (
        retro.prioridad_revision
        == "Revisa primero los indicios críticos omitidos."
    )


def test_separa_omision_critica_de_otras_omisiones() -> None:
    ejecucion = ejecutar_noticing_desde_caso(
        CASO_OBSTETRICO,
        ["cefalea_intensa"],
    )

    retro = generar_retroalimentacion_noticing(
        ejecucion.caso,
        ejecucion.resultado,
    )

    assert len(retro.omisiones_criticas) == 1
    assert len(retro.omisiones_esperadas) == 3


def test_explica_dato_no_prioritario() -> None:
    ejecucion = ejecutar_noticing_desde_caso(
        CASO_OBSTETRICO,
        [
            "pa_165_115",
            "cefalea_intensa",
            "fotofobia",
            "gestacion_36",
            "inquietud",
            "fr_20",
        ],
    )

    retro = generar_retroalimentacion_noticing(
        ejecucion.caso,
        ejecucion.resultado,
    )

    assert retro.selecciones_no_prioritarias == (
        (
            "Frecuencia respiratoria de 20 rpm. "
            "Fundamento: Sin alteracion aparente en el escenario."
        ),
    )
    assert "Revisa la priorización" in retro.prioridad_revision


def test_registra_identificador_desconocido_y_repeticion() -> None:
    ejecucion = ejecutar_noticing_desde_caso(
        CASO_OBSTETRICO,
        [
            "pa_165_115",
            "pa_165_115",
            "dato_inexistente",
        ],
    )

    retro = generar_retroalimentacion_noticing(
        ejecucion.caso,
        ejecucion.resultado,
    )

    assert retro.advertencias == (
        "Se recibieron identificadores inexistentes: dato_inexistente.",
        "Se repitieron selecciones: pa_165_115.",
    )


def test_retroalimentacion_completa_sin_errores() -> None:
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

    retro = generar_retroalimentacion_noticing(
        ejecucion.caso,
        ejecucion.resultado,
    )

    assert retro.omisiones_criticas == ()
    assert retro.omisiones_esperadas == ()
    assert retro.selecciones_no_prioritarias == ()
    assert (
        retro.prioridad_revision
        == "La selección reconoció los indicios esperados sin errores detectados."
    )


def test_como_texto_conserva_secciones_relevantes() -> None:
    ejecucion = ejecutar_noticing_desde_caso(
        CASO_OBSTETRICO,
        ["cefalea_intensa", "fr_20"],
    )

    retro = generar_retroalimentacion_noticing(
        ejecucion.caso,
        ejecucion.resultado,
    )
    texto = retro.como_texto()

    assert "Se reconocieron 1 de 5 indicios esperados." in texto
    assert "Omisiones críticas:" in texto
    assert "Datos no prioritarios seleccionados:" in texto
    assert "Prioridad de revisión:" in texto
