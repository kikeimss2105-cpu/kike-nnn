import pytest

from engine.neonatal import calcular_apgar


def test_apgar_calcula_total_desglose_e_interpretacion() -> None:
    resultado = calcular_apgar(1, 2, 2, 2, 1)
    assert resultado.total == 8
    assert dict(resultado.desglose) == {
        "apariencia": 1, "pulso": 2, "gesticulacion": 2,
        "actividad": 2, "respiracion": 1,
    }
    assert "tranquilizador" in resultado.interpretacion


@pytest.mark.parametrize("total, texto", [(0, "bajo"), (4, "moderadamente"), (7, "tranquilizador")])
def test_apgar_limites_de_interpretacion(total: int, texto: str) -> None:
    componentes = [0] * 5
    for indice in range(total // 2):
        componentes[indice] = 2
    if total % 2:
        componentes[total // 2] = 1
    assert texto in calcular_apgar(*componentes).interpretacion


def test_apgar_no_imputa_faltantes() -> None:
    resultado = calcular_apgar(None, 2, 2, 2, 1)
    assert resultado.total is None
    assert resultado.datos_faltantes == ("apariencia",)
    assert resultado.desglose["apariencia"] is None


@pytest.mark.parametrize("valor", [-1, 3, 1.0, True, "1"])
def test_apgar_rechaza_valores_invalidos(valor) -> None:
    with pytest.raises(ValueError):
        calcular_apgar(valor, 2, 2, 2, 2)
