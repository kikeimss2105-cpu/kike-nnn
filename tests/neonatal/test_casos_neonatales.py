from pathlib import Path

import yaml

from engine.neonatal.servicio import calcular_escala, serializar_resultado


CASOS = Path(__file__).resolve().parents[2] / "data" / "casos" / "neonatales"
REQUERIDOS = {
    "datos_presentados", "indicios_criticos", "resultado_esperado",
    "resultados_permitidos", "resultados_prohibidos", "fundamento_de_pertinencia",
}


def test_casos_declaran_trazabilidad_requerida() -> None:
    rutas = sorted(CASOS.glob("*.yaml"))
    assert {ruta.name for ruta in rutas} == {
        "NEO-APGAR-001.yaml", "NEO-SILVERMAN-001.yaml", "NEO-CAPURRO-001.yaml",
    }
    for ruta in rutas:
        caso = yaml.safe_load(ruta.read_text(encoding="utf-8"))
        assert REQUERIDOS <= caso.keys()
        assert all(caso[campo] for campo in REQUERIDOS)


def test_casos_ejecutables_coinciden_con_resultados_esperados() -> None:
    apgar = yaml.safe_load((CASOS / "NEO-APGAR-001.yaml").read_text())
    assert calcular_escala("apgar", apgar["datos_presentados"]).total == 8

    silverman = yaml.safe_load((CASOS / "NEO-SILVERMAN-001.yaml").read_text())
    assert calcular_escala("silverman", silverman["datos_presentados"]).total == 5

    capurro = yaml.safe_load((CASOS / "NEO-CAPURRO-001.yaml").read_text())
    datos = dict(capurro["datos_presentados"])
    datos.pop("variante")
    resultado = calcular_escala("capurro_b", datos)
    assert resultado.total == 43
    assert resultado.edad_gestacional_semanas == 247 / 7


def test_serializacion_conserva_none_y_desglose() -> None:
    resultado = calcular_escala("apgar", {
        "apariencia": None,
        "pulso": 2,
        "gesticulacion": 2,
        "actividad": 2,
        "respiracion": 1,
    })

    registro = serializar_resultado(resultado)

    assert registro["calculado"] is False
    assert registro["total"] is None
    assert registro["componentes"]["apariencia"] is None
    assert registro["datos_faltantes"] == ["apariencia"]
