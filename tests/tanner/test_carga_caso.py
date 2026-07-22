from __future__ import annotations

from pathlib import Path

import pytest

from engine.tanner.casos import cargar_caso_tanner
from engine.tanner.modelos import CategoriaIndicio


REPO_ROOT = Path(__file__).resolve().parents[2]
CASO_OBSTETRICO = REPO_ROOT / "data" / "casos" / "OBS-HTA-001.yaml"


def test_carga_caso_obstetrico_real() -> None:
    caso = cargar_caso_tanner(CASO_OBSTETRICO)

    assert caso.id == "OBS-HTA-001"
    assert caso.version == "0.1.0"
    assert caso.estado == "borrador_clinico"
    assert caso.uso_clinico_real is False
    assert "165/115" in caso.escena_inicial
    assert len(caso.indicios_noticing) == 8


def test_carga_clasifica_indicios_del_yaml() -> None:
    caso = cargar_caso_tanner(CASO_OBSTETRICO)
    por_id = {indicio.id: indicio for indicio in caso.indicios_noticing}

    assert por_id["pa_165_115"].categoria == CategoriaIndicio.CRITICO
    assert por_id["fotofobia"].categoria == CategoriaIndicio.RELEVANTE
    assert (
        por_id["pregunta_pareja"].categoria
        == CategoriaIndicio.CONTEXTO_NO_PRIORITARIO
    )


def test_carga_conserva_indicios_esperados() -> None:
    caso = cargar_caso_tanner(CASO_OBSTETRICO)

    esperados = tuple(
        indicio.id
        for indicio in caso.indicios_noticing
        if indicio.esperado
    )

    assert esperados == (
        "pa_165_115",
        "cefalea_intensa",
        "fotofobia",
        "gestacion_36",
        "inquietud",
    )


def test_rechaza_archivo_inexistente(tmp_path: Path) -> None:
    ruta = tmp_path / "caso-inexistente.yaml"

    with pytest.raises(FileNotFoundError, match="No existe"):
        cargar_caso_tanner(ruta)


def test_rechaza_yaml_sin_campos_obligatorios(tmp_path: Path) -> None:
    ruta = tmp_path / "incompleto.yaml"
    ruta.write_text("id: CASO-001\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Faltan campos obligatorios"):
        cargar_caso_tanner(ruta)


def test_rechaza_categoria_desconocida(tmp_path: Path) -> None:
    ruta = tmp_path / "categoria-invalida.yaml"
    ruta.write_text(
        """
id: CASO-001
version: "1.0"
estado: prueba
titulo: Caso de prueba
proposito:
  uso_clinico_real: false
escena_inicial:
  texto: Escena de prueba
tanner:
  noticing:
    indicios:
      - id: dato
        texto: Dato de prueba
        categoria: categoria_inventada
        esperado: true
        fundamento: Fundamento
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Categoría inválida"):
        cargar_caso_tanner(ruta)
