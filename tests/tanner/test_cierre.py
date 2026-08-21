from pathlib import Path

from engine.tanner.cierre import BLOQUEO_CLINICO, inspeccionar_cierre_tanner


CASO = Path("data/casos/OBS-HTA-001.yaml")


def test_caso_actual_habilita_solo_fases_implementadas() -> None:
    estado = inspeccionar_cierre_tanner(CASO)

    assert estado.caso_id == "OBS-HTA-001"
    assert estado.noticing_definido is True
    assert estado.interpreting_definido is True
    assert estado.responding_habilitado is True
    assert estado.reflecting_habilitado is True
    assert estado.farmacologia_habilitada is False
    assert estado.maquina_estados_habilitada is False
    assert estado.ciclo_completo_habilitado is False


def test_limites_no_validados_quedan_bloqueados_explicita_y_reproduciblemente() -> None:
    estado = inspeccionar_cierre_tanner(CASO)

    assert len(estado.bloqueos) == 2
    assert all(mensaje.startswith(BLOQUEO_CLINICO) for mensaje in estado.bloqueos)
    assert any("Farmacología" in mensaje for mensaje in estado.bloqueos)
    assert any("máquina de estados" in mensaje for mensaje in estado.bloqueos)
