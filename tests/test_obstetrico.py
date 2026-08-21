from __future__ import annotations

import pytest

from engine.interpretaciones import interpretar_pa_obstetrica
from engine.obstetrico import (
    evaluar_rutas_obstetricas,
    extraer_hallazgos_obstetricos,
    generar_alertas_obstetricas,
)


def _alertas(**cambios):
    datos = {
        "tipo_paciente": "Obstétrico",
        "semanas_gestacion": None,
        "pas": None,
        "pad": None,
        "temperatura": None,
        "cefalea_intensa": False,
        "fosfenos": False,
        "acufenos": False,
        "epigastralgia": False,
        "edema_cara_manos": False,
        "convulsiones": False,
        "sangrado_vaginal": False,
        "salida_liquido": False,
        "liquido_fetido": False,
        "liquido_verdoso": False,
        "dolor_abdominal_intenso": False,
        "contracciones_antes_termino": False,
        "disminucion_mov_fetales": False,
        "nausea_vomito_persistente": False,
        "disuria_obstetrica": False,
    }
    datos.update(cambios)
    return generar_alertas_obstetricas(**datos)


@pytest.mark.parametrize(
    ("pas", "pad", "esperado"),
    [
        (139, 89, "Sin umbral de PA elevada"),
        (140, 90, "PA elevada desde semana 20 o más"),
        (140, 80, "PA elevada desde semana 20 o más"),
        (120, 90, "PA elevada desde semana 20 o más"),
        (159, 109, "PA elevada desde semana 20 o más"),
        (160, 110, "PA en rango severo"),
        (160, 80, "PA en rango severo"),
        (120, 110, "PA en rango severo"),
    ],
)
def test_fronteras_pa_y_operador_or(pas, pad, esperado):
    assert esperado in interpretar_pa_obstetrica(pas, pad, 20)


def test_pa_elevada_solo_etiqueta_contexto_gestacional_desde_semana_20():
    datos_19, resumen_19 = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=19, pa_sistolica=140, pa_diastolica=90
    )
    datos_20, resumen_20 = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=20, pa_sistolica=140, pa_diastolica=90
    )

    assert datos_19 == []
    assert resumen_19.startswith("Sin ruta")
    assert "preeclampsia" not in " ".join(datos_20).lower()
    assert "PA 140/90 desde semana 20 o más" in resumen_20


def test_pa_severa_antes_de_semana_20_es_urgente_sin_etiqueta_gestacional():
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=19, pa_sistolica=160, pa_diastolica=80
    )
    assert resumen.startswith("[Crítica]")
    assert "trastorno hipertensivo del embarazo" not in " ".join(datos)


def test_none_permanece_no_valorado_y_no_activa_reglas():
    assert "no valorada" in interpretar_pa_obstetrica(None, None, None).lower()
    assert _alertas() == []
    datos, resumen = evaluar_rutas_obstetricas("Obstétrico")
    assert datos == []
    assert resumen.startswith("Sin ruta")


@pytest.mark.parametrize("temperatura,activa", [(37.9, False), (38.0, True)])
def test_frontera_temperatura(temperatura, activa):
    _, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=30, temperatura=temperatura
    )
    assert ("fiebre" in resumen.lower()) is activa


@pytest.mark.parametrize(
    "sintoma",
    ["cefalea", "fosfenos", "acufenos", "epigastralgia", "convulsiones"],
)
def test_sintomas_hipertensivos_aislados_son_alarma_sin_preeclampsia(sintoma):
    _, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=20, **{sintoma: True}
    )
    assert "Evaluación de trastorno hipertensivo" in resumen
    assert "preeclampsia" not in resumen.lower()


def test_sangrado_sin_dolor_no_fabrica_dolor():
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=30, sangrado=True
    )
    hallazgos = extraer_hallazgos_obstetricos(
        "Obstétrico", semanas_gestacion=30, sangrado_vaginal=True
    )
    assert "Hemorrágica" in resumen
    datos_activadores = resumen.split("Acción educativa:", 1)[0]
    assert "dolor" not in datos_activadores.lower()
    assert not any("dolor" in dato for dato in datos + hallazgos)


def test_liquido_fetido_sin_temperatura_no_fabrica_fiebre_ni_infeccion_confirmada():
    hallazgos = extraer_hallazgos_obstetricos(
        "Obstétrico", semanas_gestacion=30, liquido_fetido=True, temperatura=None
    )
    alertas = _alertas(semanas_gestacion=30, liquido_fetido=True)
    texto = " ".join(hallazgos + [str(alerta) for alerta in alertas]).lower()
    assert "fiebre" not in texto
    assert "posible riesgo de infección" in texto
    assert "infección confirmada" not in texto
    datos, _ = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=30, liquido_fetido=True, temperatura=None
    )
    assert "salida de líquido transvaginal" not in datos
    assert "sospecha de ruptura de membranas" not in datos


def test_salida_liquido_es_sospecha_y_no_diagnostico_definitivo():
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=36, salida_liquido=True
    )
    assert "sospecha de ruptura de membranas" in " ".join(datos).lower()
    assert "Valorar posible ruptura" in resumen


def test_disuria_no_fabrica_diagnostico_de_infeccion_urinaria():
    hallazgos = extraer_hallazgos_obstetricos("Obstétrico", disuria_obstetrica=True)
    assert "disuria" in hallazgos
    assert "posible riesgo urinario" in hallazgos
    assert "infección urinaria" not in hallazgos


@pytest.mark.parametrize(
    ("semanas", "activa"),
    [(36, True), (37, False)],
)
def test_contracciones_antes_de_termino_exigen_menos_de_37_semanas(semanas, activa):
    _, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=semanas, contracciones=True
    )
    assert ("contracciones antes de término" in resumen) is activa


def test_contracciones_textuales_tambien_exigen_menos_de_37_semanas():
    _, resumen_36 = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=36,
        hallazgos_detectados=["contracciones antes de término"],
    )
    _, resumen_37 = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=37,
        hallazgos_detectados=["contracciones antes de término"],
    )
    assert "contracciones antes de término" in resumen_36
    assert "contracciones antes de término" not in resumen_37


@pytest.mark.parametrize(("semanas", "activa"), [(19, False), (20, True)])
def test_movimientos_fetales_aplican_criterio_gestacional_sin_diagnosticar(semanas, activa):
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=semanas, movimientos_fetales="Ausentes"
    )
    assert ("Bienestar fetal" in resumen) is activa
    texto = " ".join(datos).lower()
    assert "diagnóstico fetal" not in texto
    assert "sufrimiento fetal" not in texto


def test_tipo_invalido_es_fallo_tecnico_y_no_resultado_clinico_negativo():
    with pytest.raises(TypeError):
        evaluar_rutas_obstetricas(
            "Obstétrico", semanas_gestacion="veinte", pa_sistolica="alta"
        )
