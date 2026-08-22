from __future__ import annotations

from pathlib import Path

import pytest

from engine.interpretaciones import interpretar_pa_obstetrica
from engine.obstetrico import (
    clasificar_datos_rpm,
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


def test_sangrado_booleano_conserva_dato_sangrado_vaginal():
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=30, sangrado=True
    )
    hallazgos = extraer_hallazgos_obstetricos(
        "Obstétrico", semanas_gestacion=30, sangrado_vaginal=True
    )
    assert "Sangrado obstétrico / requiere valoración" in resumen
    datos_activadores = resumen.split("Acción educativa:", 1)[0]
    assert "dolor" not in datos_activadores.lower()
    assert not any("dolor" in dato for dato in datos + hallazgos)
    assert hallazgos == [
        "embarazo", "paciente obstétrica", "vigilancia obstétrica",
        "embarazo mayor de 20 semanas", "sangrado vaginal",
    ]


def test_sangrado_aislado_no_genera_dolor():
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=30, sangrado=True
    )
    datos_activadores = resumen.split("Acción educativa:", 1)[0]
    assert "dolor" not in datos_activadores.lower()
    assert not any("dolor" in dato for dato in datos)


def test_sangrado_aislado_no_genera_compromiso_fetal():
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=30, sangrado=True
    )
    texto = " ".join(datos + [resumen]).lower()
    assert "compromiso fetal" not in texto
    assert "riesgo de alteración de la díada materno-fetal" not in datos


def test_sangrado_aislado_no_genera_choque():
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=30, sangrado=True
    )
    assert "choque" not in " ".join(datos + [resumen]).lower()


def test_sangrado_aislado_no_se_denomina_hemorragia_confirmada():
    _, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=30, sangrado=True
    )
    assert "hemorragia confirmada" not in resumen.lower()
    assert "Hemorrágica" not in resumen
    assert "Sangrado obstétrico / requiere valoración" in resumen


@pytest.mark.parametrize("termino", ["hemorragia", "sangrado obstétrico"])
def test_termino_general_de_sangrado_no_infiere_localizacion_vaginal(termino):
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=30, hallazgos_detectados=[termino]
    )
    assert termino in datos
    assert "sangrado vaginal" not in datos
    assert termino in resumen


def test_texto_sangrado_vaginal_se_reconoce_correctamente():
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=30,
        hallazgos_detectados=["sangrado vaginal"],
    )
    assert datos == ["sangrado vaginal"]
    assert "sangrado vaginal" in resumen


def test_ruta_no_reutiliza_etiquetas_nanda_como_datos_de_entrada():
    datos, _ = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=30, sangrado=True
    )
    assert "riesgo de sangrado" not in datos
    assert "riesgo de alteración de la díada materno-fetal" not in datos


def test_ausencia_de_datos_fetales_se_conserva_como_ausencia():
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=30, sangrado=True,
        movimientos_fetales="No aplica / no valorado",
    )
    texto = " ".join(datos + [resumen]).lower()
    assert "movimientos fetales" not in texto
    assert "díada materno-fetal" not in texto
    assert "bienestar fetal" not in texto


def test_salida_visual_de_sangrado_no_usa_triaje_o_gravedad_no_validada():
    app = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")
    assert "Situaciones obstétricas que requieren valoración" in app
    assert 'st.error(f"⚠️ Posibles alertas detectadas")' not in app
    assert "Rutas: hipertensiva, RPM/infección, dolor obstétrico, hemorrágica" not in app


def test_alerta_de_sangrado_sugiere_valoracion_sin_confirmar_diagnosticos():
    [alerta] = _alertas(semanas_gestacion=30, sangrado_vaginal=True)
    assert alerta["Nivel"] == "Requiere valoración"
    assert alerta["Alerta"] == (
        "Sangrado vaginal durante el embarazo: requiere valoración obstétrica y caracterización."
    )
    texto = " ".join(alerta.values()).lower()
    assert "hemorragia confirmada" not in texto
    assert "choque" not in texto
    assert "compromiso fetal" not in texto


def test_liquido_fetido_sin_temperatura_no_fabrica_fiebre_ni_infeccion_confirmada():
    hallazgos = extraer_hallazgos_obstetricos(
        "Obstétrico", semanas_gestacion=30, liquido_fetido=True, temperatura=None
    )
    alertas = _alertas(semanas_gestacion=30, liquido_fetido=True)
    texto = " ".join(hallazgos + [str(alerta) for alerta in alertas]).lower()
    assert "fiebre" not in texto
    categorias = clasificar_datos_rpm(liquido_fetido=True, temperatura=None)
    assert "posible riesgo infeccioso" in categorias["SOSPECHAS"]
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
    assert "rpm confirmada" not in resumen.lower()
    assert "ruptura prematura de membranas confirmada" not in resumen.lower()


def test_salida_liquido_sin_edad_gestacional_conserva_no_valorado():
    categorias = clasificar_datos_rpm(salida_liquido=True)
    [alerta] = _alertas(salida_liquido=True, semanas_gestacion=None)

    assert categorias["DATOS_OBSERVADOS"] == ["salida de líquido transvaginal"]
    assert "sospecha de ruptura de membranas" in categorias["SOSPECHAS"]
    assert "edad gestacional no valorada" in alerta["Alerta"]


@pytest.mark.parametrize(
    ("semanas", "clasificacion"),
    [(36, "gestación pretérmino"), (37, "gestación a término")],
)
def test_salida_liquido_distingue_semana_36_y_37(semanas, clasificacion):
    [alerta] = _alertas(salida_liquido=True, semanas_gestacion=semanas)
    assert clasificacion in alerta["Alerta"]


def test_fiebre_aislada_no_genera_corioamnionitis():
    categorias = clasificar_datos_rpm(temperatura=38.0)
    alertas = _alertas(temperatura=38.0)
    _, resumen = evaluar_rutas_obstetricas("Obstétrico", temperatura=38.0)
    texto = " ".join(
        sum(categorias.values(), []) + [str(alertas), resumen]
    ).lower()
    assert "fiebre" in texto
    assert "corioamnionitis" not in texto
    assert "infección confirmada" not in texto


def test_liquido_verdoso_no_fabrica_compromiso_fetal():
    categorias = clasificar_datos_rpm(liquido_verdoso=True)
    alertas = _alertas(liquido_verdoso=True)
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", liquido_verdoso=True,
        movimientos_fetales="No aplica / no valorado",
    )
    texto = " ".join(sum(categorias.values(), []) + datos + [str(alertas), resumen]).lower()
    assert "líquido verdoso" in texto
    assert "compromiso fetal" not in texto
    assert "sufrimiento fetal" not in texto
    assert "alteración de la díada" not in texto


def test_dolor_y_contracciones_ausentes_permanecen_ausentes_en_ruta_rpm():
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=36, salida_liquido=True,
        dolor_abdominal=False, contracciones=False,
    )
    activadores = resumen.split("Acción educativa:", 1)[0].lower()
    assert "dolor" not in activadores
    assert "contracciones" not in activadores
    assert not any("dolor" in dato or "contracciones" in dato for dato in datos)


def test_ruta_rpm_separa_observado_sospecha_y_sugerencia_nanda():
    categorias = clasificar_datos_rpm(
        salida_liquido=True, liquido_fetido=True, temperatura=38.0,
    )
    assert categorias["DATOS_OBSERVADOS"] == [
        "salida de líquido transvaginal", "líquido fétido", "temperatura medida 38.0°C",
    ]
    assert categorias["INFERENCIAS_PEDAGOGICAS"] == ["fiebre"]
    assert "sospecha de ruptura de membranas" in categorias["SOSPECHAS"]
    assert categorias["SUGERENCIAS_NANDA"] == []


def test_sin_dato_fetal_no_genera_nanda_materno_fetal_ni_estado_fetal():
    pytest.importorskip("pandas")
    from engine.carga import cargar_catalogos
    from engine.motor import buscar_diagnosticos

    catalogos = cargar_catalogos("data")
    categorias = clasificar_datos_rpm(
        salida_liquido=True, liquido_fetido=True, liquido_verdoso=True,
    )
    texto_observado = "Obstétrico embarazo " + " ".join(categorias["DATOS_OBSERVADOS"])
    resultados = buscar_diagnosticos(texto_observado, catalogos.nanda, catalogos.enlaces)

    if not resultados.empty:
        assert not resultados["NANDA"].str.contains("materno-fetal", case=False).any()
        assert not resultados["NOC sugerido"].str.contains("Estado fetal", case=False).any()


def test_etiquetas_de_ruta_no_se_reutilizan_como_evidencia_nanda():
    categorias = clasificar_datos_rpm(salida_liquido=True, liquido_fetido=True)
    texto_observado = " ".join(categorias["DATOS_OBSERVADOS"])
    assert "sospecha de ruptura" not in texto_observado
    assert "riesgo" not in texto_observado
    assert categorias["SUGERENCIAS_NANDA"] == []


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
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=semanas, contracciones=True
    )
    assert ("contracciones uterinas en gestación pretérmino" in resumen.lower()) is activa
    assert ("contracciones en gestación pretérmino" in datos) is activa


def test_contracciones_textuales_tambien_exigen_menos_de_37_semanas():
    _, resumen_36 = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=36,
        hallazgos_detectados=["contracciones antes de término"],
    )
    _, resumen_37 = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=37,
        hallazgos_detectados=["contracciones antes de término"],
    )
    assert "contracciones uterinas en gestación pretérmino" in resumen_36.lower()
    assert "contracciones uterinas en gestación pretérmino" not in resumen_37.lower()


@pytest.mark.parametrize("semanas", [None, 0, -1, 43])
def test_edad_gestacional_no_valorada_o_fuera_de_rango_no_clasifica_pretermino(semanas):
    hallazgos = extraer_hallazgos_obstetricos(
        "Obstétrico", semanas_gestacion=semanas,
        contracciones_antes_termino=True,
    )
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=semanas, contracciones=True,
    )
    alertas = _alertas(
        semanas_gestacion=semanas, contracciones_antes_termino=True,
    )

    assert "contracciones uterinas" in hallazgos
    assert "contracciones en gestación pretérmino" not in hallazgos
    assert "contracciones en gestación pretérmino" not in datos
    assert "gestación pretérmino" not in resumen
    assert not any("gestación pretérmino" in str(alerta) for alerta in alertas)


def test_contracciones_a_36_requieren_valoracion_sin_diagnosticar():
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=36, contracciones=True,
    )
    alertas = _alertas(
        semanas_gestacion=36, contracciones_antes_termino=True,
    )
    texto = " ".join(datos + [resumen, str(alertas)]).lower()

    assert "contracciones uterinas en gestación pretérmino" in texto
    assert "requiere valoración" in texto
    assert "amenaza de parto pretérmino" not in texto
    assert "trabajo de parto pretérmino" not in texto
    assert "parto pretérmino" not in texto


def test_contracciones_aisladas_no_generan_dolor_ni_riesgo_de_diada():
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=36, contracciones=True,
    )
    activadores = resumen.split("Acción educativa:", 1)[0].lower()

    assert "dolor" not in activadores
    assert not any("dolor" in dato for dato in datos)
    assert "riesgo de alteración de la díada materno-fetal" not in datos


def test_contracciones_aisladas_no_generan_nanda_noc_nic_de_dolor():
    pytest.importorskip("pandas")
    from engine.carga import cargar_catalogos
    from engine.motor import buscar_diagnosticos

    catalogos = cargar_catalogos("data")
    hallazgos = extraer_hallazgos_obstetricos(
        "Obstétrico", semanas_gestacion=36,
        contracciones_antes_termino=True,
    )
    resultados = buscar_diagnosticos(" ".join(hallazgos), catalogos.nanda, catalogos.enlaces)

    if not resultados.empty:
        assert "Dolor de parto" not in resultados["NANDA"].tolist()
        assert not resultados["NOC sugerido"].str.contains(
            "Control del dolor|Bienestar materno", case=False, regex=True,
        ).any()
        assert not resultados["NIC sugerido"].str.contains(
            "Manejo del dolor del parto|Apoyo emocional", case=False, regex=True,
        ).any()


def test_contracciones_y_sangrado_permanecen_en_rutas_separadas_sin_dolor():
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=36,
        contracciones=True, sangrado=True,
    )
    assert "Sangrado obstétrico / requiere valoración" in resumen
    assert "Contracciones uterinas en gestación pretérmino" in resumen
    assert not any("dolor" in dato for dato in datos)


@pytest.mark.parametrize(
    ("cambios", "ruta_adicional"),
    [
        ({"salida_liquido": True}, "Salida de líquido / sospecha de ruptura de membranas"),
        ({"temperatura": 38.0}, "Signos que requieren valoración de infección"),
        ({"movimientos_fetales": "Disminuidos"}, "Bienestar fetal"),
    ],
)
def test_interacciones_con_contracciones_no_fabrican_dolor_ni_diagnostico(cambios, ruta_adicional):
    datos, resumen = evaluar_rutas_obstetricas(
        "Obstétrico", semanas_gestacion=36, contracciones=True, **cambios,
    )
    assert ruta_adicional in resumen
    assert "Contracciones uterinas en gestación pretérmino" in resumen
    assert not any("dolor" in dato for dato in datos)
    assert "riesgo de alteración de la díada materno-fetal" not in datos
    assert "amenaza de parto pretérmino" not in resumen.lower()
    assert "trabajo de parto pretérmino" not in resumen.lower()
    assert "parto pretérmino" not in resumen.lower()


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
