import inspect

import pytest

from engine.neonatal import calcular_capurro_a, calcular_capurro_b


def test_capurro_a_usa_seis_componentes_y_constante_200() -> None:
    resultado = calcular_capurro_a(8, 10, 10, 10, 12, 8)
    assert resultado.total == 58
    assert resultado.formula == "(200 + suma de componentes) / 7"
    assert resultado.edad_gestacional_semanas == 258 / 7
    assert (resultado.semanas_completas, resultado.dias_adicionales) == (36, 6)


def test_capurro_b_usa_cinco_componentes_y_constante_204() -> None:
    resultado = calcular_capurro_b(8, 10, 10, 10, 5)
    assert resultado.total == 43
    assert resultado.formula == "(204 + suma de componentes) / 7"
    assert resultado.edad_gestacional_semanas == 247 / 7
    assert (resultado.semanas_completas, resultado.dias_adicionales) == (35, 2)


@pytest.mark.parametrize("calculador, datos", [
    (calcular_capurro_a, (8, 10, 10, 10, None, 8)),
    (calcular_capurro_b, (8, 10, None, 10, 5)),
])
def test_capurro_no_calcula_con_obligatorio_faltante(calculador, datos) -> None:
    resultado = calculador(*datos)
    assert resultado.total is None
    assert resultado.edad_gestacional_semanas is None
    assert resultado.datos_faltantes


def test_capurro_rechaza_puntaje_que_no_pertenece_al_criterio() -> None:
    with pytest.raises(ValueError):
        calcular_capurro_b(7, 10, 10, 10, 5)


def test_variantes_capurro_tienen_componentes_y_constantes_exclusivos() -> None:
    parametros_a = tuple(inspect.signature(calcular_capurro_a).parameters)
    parametros_b = tuple(inspect.signature(calcular_capurro_b).parameters)

    assert parametros_a == (
        "forma_oreja",
        "tamano_glandula_mamaria",
        "textura_piel",
        "pliegues_plantares",
        "signo_bufanda",
        "caida_cabeza",
    )
    assert "formacion_pezon" not in parametros_a
    assert parametros_b == (
        "forma_oreja",
        "tamano_glandula_mamaria",
        "formacion_pezon",
        "textura_piel",
        "pliegues_plantares",
    )
    assert "signo_bufanda" not in parametros_b
    assert "caida_cabeza" not in parametros_b

    with pytest.raises(TypeError):
        calcular_capurro_a(
            forma_oreja=8,
            tamano_glandula_mamaria=10,
            textura_piel=10,
            signo_bufanda=12,
            caida_cabeza=8,
        )
    with pytest.raises(TypeError):
        calcular_capurro_a(
            forma_oreja=8,
            tamano_glandula_mamaria=10,
            formacion_pezon=10,
            textura_piel=10,
            signo_bufanda=12,
            caida_cabeza=8,
        )
    with pytest.raises(TypeError):
        calcular_capurro_b(
            forma_oreja=8,
            tamano_glandula_mamaria=10,
            formacion_pezon=10,
            textura_piel=10,
            pliegues_plantares=5,
            signo_bufanda=12,
        )

    resultado_a = calcular_capurro_a(8, 10, 10, 10, 12, 8)
    resultado_b = calcular_capurro_b(8, 10, 10, 10, 5)
    assert resultado_a.formula == "(200 + suma de componentes) / 7"
    assert resultado_b.formula == "(204 + suma de componentes) / 7"
