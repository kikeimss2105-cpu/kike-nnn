from pathlib import Path

from engine.tanner.cierre import BLOQUEO_CLINICO, inspeccionar_cierre_tanner


CASO = Path("data/casos/OBS-HTA-001.yaml")


def test_caso_actual_habilita_solo_fases_implementadas() -> None:
    estado = inspeccionar_cierre_tanner(CASO)

    assert estado.caso_id == "OBS-HTA-001"
    assert estado.noticing_definido is True
    assert estado.interpreting_definido is True
    assert estado.responding_habilitado is False
    assert estado.reflecting_habilitado is False
    assert estado.ciclo_completo_habilitado is False


def test_fases_no_validadas_quedan_bloqueadas_explicita_y_reproduciblemente() -> None:
    estado = inspeccionar_cierre_tanner(CASO)

    assert len(estado.bloqueos) == 2
    assert all(mensaje.startswith(BLOQUEO_CLINICO) for mensaje in estado.bloqueos)
    assert any("Responding" in mensaje for mensaje in estado.bloqueos)
    assert any("Reflecting" in mensaje for mensaje in estado.bloqueos)
