import pytest

from engine.neonatal import calcular_silverman


@pytest.mark.parametrize(
    "componentes, total, clasificacion",
    [((0, 0, 0, 0, 0), 0, "Sin dificultad"),
     ((1, 0, 0, 0, 0), 1, "leve"),
     ((1, 1, 1, 1, 0), 4, "moderada"),
     ((2, 2, 1, 1, 1), 7, "grave")],
)
def test_silverman_total_y_clasificacion(componentes, total, clasificacion) -> None:
    resultado = calcular_silverman(*componentes)
    assert resultado.total == total
    assert clasificacion in resultado.interpretacion
    assert len(resultado.desglose) == 5


def test_silverman_no_calcula_con_faltante() -> None:
    resultado = calcular_silverman(0, None, 0, 0, 0)
    assert resultado.total is None
    assert resultado.datos_faltantes == ("tiraje_intercostal",)


def test_silverman_valida_componentes() -> None:
    with pytest.raises(ValueError):
        calcular_silverman(0, 0, 0, 0, 3)
