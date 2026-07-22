from __future__ import annotations

import pytest

from engine.tanner import (
    CategoriaIndicio,
    IndicioTanner,
    evaluar_noticing,
)


@pytest.fixture
def indicios_caso() -> tuple[IndicioTanner, ...]:
    return (
        IndicioTanner(
            id="pa_165_115",
            texto="Presión arterial de 165/115 mmHg",
            categoria=CategoriaIndicio.CRITICO,
            esperado=True,
            fundamento="Hipertensión grave.",
        ),
        IndicioTanner(
            id="cefalea_intensa",
            texto="Cefalea intensa",
            categoria=CategoriaIndicio.CRITICO,
            esperado=True,
            fundamento="Manifestación neurológica de alarma.",
        ),
        IndicioTanner(
            id="fotofobia",
            texto="Molestia importante ante la luz",
            categoria=CategoriaIndicio.RELEVANTE,
            esperado=True,
            fundamento="Síntoma neurológico que requiere valoración.",
        ),
        IndicioTanner(
            id="gestacion_36",
            texto="Embarazo de 36 semanas",
            categoria=CategoriaIndicio.CONTEXTO_ESENCIAL,
            esperado=True,
            fundamento="Contexto obstétrico.",
        ),
        IndicioTanner(
            id="inquietud",
            texto="Paciente inquieta",
            categoria=CategoriaIndicio.COMPLEMENTARIO,
            esperado=True,
            fundamento="Dato inespecífico que requiere contexto.",
        ),
        IndicioTanner(
            id="fr_20",
            texto="Frecuencia respiratoria de 20 rpm",
            categoria=CategoriaIndicio.DATO_NO_PRIORITARIO,
            esperado=False,
            fundamento="Sin alteración aparente en este escenario.",
        ),
        IndicioTanner(
            id="pregunta_pareja",
            texto="La pareja pregunta si el nacimiento ocurrirá hoy",
            categoria=CategoriaIndicio.CONTEXTO_NO_PRIORITARIO,
            esperado=False,
            fundamento=(
                "Requiere respuesta posterior sin desplazar la atención urgente."
            ),
        ),
    )


def test_reconoce_todos_los_indicios_esperados(indicios_caso) -> None:
    resultado = evaluar_noticing(
        indicios_caso,
        [
            "pa_165_115",
            "cefalea_intensa",
            "fotofobia",
            "gestacion_36",
            "inquietud",
        ],
    )

    assert resultado.completo_sin_errores is True
    assert resultado.omitidos_esperados == ()
    assert resultado.omisiones_criticas == ()
    assert resultado.seleccionados_no_prioritarios == ()


def test_detecta_omision_critica_de_presion(indicios_caso) -> None:
    resultado = evaluar_noticing(
        indicios_caso,
        ["cefalea_intensa", "fotofobia", "gestacion_36", "inquietud"],
    )

    assert resultado.tiene_omisiones_criticas is True
    assert resultado.omisiones_criticas == ("pa_165_115",)


def test_distingue_omision_relevante_de_omision_critica(indicios_caso) -> None:
    resultado = evaluar_noticing(
        indicios_caso,
        ["pa_165_115", "cefalea_intensa", "gestacion_36", "inquietud"],
    )

    assert resultado.omitidos_esperados == ("fotofobia",)
    assert resultado.omisiones_criticas == ()


def test_identifica_datos_no_prioritarios_seleccionados(indicios_caso) -> None:
    resultado = evaluar_noticing(
        indicios_caso,
        ["pa_165_115", "fr_20", "pregunta_pareja"],
    )

    assert resultado.seleccionados_no_prioritarios == (
        "fr_20",
        "pregunta_pareja",
    )


def test_registra_identificador_desconocido_sin_romper(indicios_caso) -> None:
    resultado = evaluar_noticing(
        indicios_caso,
        ["pa_165_115", "dato_inexistente"],
    )

    assert resultado.seleccion_valida is False
    assert resultado.identificadores_desconocidos == ("dato_inexistente",)
    assert resultado.seleccionados == ("pa_165_115",)


def test_registra_selecciones_repetidas(indicios_caso) -> None:
    resultado = evaluar_noticing(
        indicios_caso,
        ["pa_165_115", "pa_165_115", "cefalea_intensa"],
    )

    assert resultado.seleccion_repetida == ("pa_165_115",)
    assert resultado.seleccionados == ("pa_165_115", "cefalea_intensa")


def test_no_seleccionar_nada_omite_todos_los_esperados(indicios_caso) -> None:
    resultado = evaluar_noticing(indicios_caso, [])

    assert resultado.reconocidos_esperados == ()
    assert resultado.omitidos_esperados == (
        "pa_165_115",
        "cefalea_intensa",
        "fotofobia",
        "gestacion_36",
        "inquietud",
    )
    assert resultado.omisiones_criticas == (
        "pa_165_115",
        "cefalea_intensa",
    )


def test_rechaza_identificadores_duplicados_en_el_caso() -> None:
    indicios = (
        IndicioTanner(
            id="duplicado",
            texto="Dato uno",
            categoria=CategoriaIndicio.CRITICO,
            esperado=True,
            fundamento="Fundamento uno.",
        ),
        IndicioTanner(
            id="duplicado",
            texto="Dato dos",
            categoria=CategoriaIndicio.RELEVANTE,
            esperado=True,
            fundamento="Fundamento dos.",
        ),
    )

    with pytest.raises(ValueError, match="deben ser únicos"):
        evaluar_noticing(indicios, ["duplicado"])


@pytest.mark.parametrize(
    ("id_indicio", "texto", "fundamento"),
    [
        ("", "Dato", "Fundamento"),
        ("dato", "", "Fundamento"),
        ("dato", "Dato", ""),
    ],
)
def test_indicio_rechaza_campos_vacios(
    id_indicio: str,
    texto: str,
    fundamento: str,
) -> None:
    with pytest.raises(ValueError):
        IndicioTanner(
            id=id_indicio,
            texto=texto,
            categoria=CategoriaIndicio.RELEVANTE,
            esperado=True,
            fundamento=fundamento,
        )
