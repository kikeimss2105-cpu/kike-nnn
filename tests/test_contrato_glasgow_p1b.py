from itertools import product
from pathlib import Path

import pandas as pd
import pytest

from engine.evidencia import (
    ElegibilidadEvidencia,
    EstadoValidacion,
    FuenteEvidencia,
    NaturalezaEvidencia,
    evidencia_estructurada,
)
from engine.glasgow import (
    OPCIONES_MOTORA,
    OPCIONES_OCULAR,
    OPCIONES_VERBAL,
    actualizar_datos_paciente_glasgow,
    alertas_desde_glasgow,
    evaluar_glasgow,
    resolver_id_valoracion,
    sincronizar_alertas_glasgow,
)
from engine.motor import SCORING_KIKE_NNN_V1, calcular_puntaje_evidencias
from engine.resumen import generar_alertas_clinicas, generar_resumen_clinico


RAIZ = Path(__file__).resolve().parents[1]
PROHIBIDOS = {
    "confusión",
    "somnolencia",
    "riesgo de caídas",
    "dificultad para caminar",
    "riesgo de aspiración",
    "disminución del reflejo tusígeno",
    "respuesta verbal alterada",
    "respuesta motora alterada",
    "dependencia para higiene",
    "inmovilidad",
    "deterioro neurológico",
}


def valorar(ocular=4, verbal=5, motora=6, episodio="gcs-episodio-1"):
    return evaluar_glasgow(
        ocular,
        verbal,
        motora,
        valorado=True,
        id_valoracion=episodio,
    )


def conceptos(resultado):
    return {e.concepto.lower() for e in resultado.evidencias}


def alertas_generales(resultado):
    return generar_alertas_clinicas(
        spo2=None,
        fr=None,
        eva_dolor=0,
        puntaje_braden=23,
        glasgow_total=resultado.total,
        puntaje_caidas=0,
        riesgo_caidas="No valorado",
        hallazgos_seleccionados=[],
        resultado_glasgow=resultado,
    )


def test_i29_no_valorado_no_es_quince_y_no_produce_salidas():
    resultado = evaluar_glasgow(4, 5, 6, valorado=False, id_valoracion="ignorado")
    assert not resultado.valorado
    assert resultado.id_valoracion is None
    assert resultado.total is None
    assert resultado.interpretacion is None
    assert resultado.evidencias == ()
    assert alertas_desde_glasgow(resultado) == []
    assert alertas_generales(resultado) == []


def test_i30_i34_opciones_y_numero_de_combinaciones_son_explícitos():
    assert set(OPCIONES_OCULAR) == {1, 2, 3, 4}
    assert set(OPCIONES_VERBAL) == {1, 2, 3, 4, 5}
    assert set(OPCIONES_MOTORA) == {1, 2, 3, 4, 5, 6}
    combinaciones = list(product(OPCIONES_OCULAR, OPCIONES_VERBAL, OPCIONES_MOTORA))
    assert len(combinaciones) == 120


@pytest.mark.parametrize(
    "ocular,verbal,motora",
    list(product(OPCIONES_OCULAR, OPCIONES_VERBAL, OPCIONES_MOTORA)),
)
def test_i30_i32_i34_las_120_combinaciones_preservan_componentes_y_total(
    ocular, verbal, motora
):
    resultado = valorar(ocular, verbal, motora)
    assert resultado.valorado
    assert (resultado.ocular.valor, resultado.verbal.valor, resultado.motora.valor) == (
        ocular, verbal, motora
    )
    assert resultado.total == ocular + verbal + motora
    assert len(resultado.evidencias) == 5


def test_i31_i33_identidad_y_genealogia_del_total():
    resultado = valorar(3, 4, 5, episodio="valoracion-42")
    assert resultado.id_valoracion == "valoracion-42"
    assert resultado.ids_progenitores_total == (
        "valoracion-42:ocular",
        "valoracion-42:verbal",
        "valoracion-42:motora",
    )
    assert resultado.evidencia_total.derivada_de == "valoracion-42"
    assert {e.id_dato_primario for e in resultado.evidencias[:3]} == set(
        resultado.ids_progenitores_total
    )


def test_i31_valoraciones_automaticas_reciben_identidades_distintas():
    primera = evaluar_glasgow(4, 5, 6, valorado=True)
    segunda = evaluar_glasgow(4, 5, 6, valorado=True)
    assert primera.id_valoracion
    assert segunda.id_valoracion
    assert primera.id_valoracion != segunda.id_valoracion


@pytest.mark.parametrize(
    "ocular,verbal,motora",
    [
        (0, 5, 6), (5, 5, 6), (None, 5, 6),
        (4, 0, 6), (4, 6, 6), (4, None, 6),
        (4, 5, 0), (4, 5, 7), (4, 5, None),
        (True, 5, 6), (4.0, 5, 6), ("4", 5, 6),
        (4, True, 6), (4, 5.0, 6), (4, "5", 6),
        (4, 5, True), (4, 5, 6.0), (4, 5, "6"),
    ],
)
def test_i34_i35_limites_invalidos_fallan_cerrados(ocular, verbal, motora):
    resultado = evaluar_glasgow(
        ocular, verbal, motora, valorado=True, id_valoracion="invalida"
    )
    assert not resultado.valorado
    assert resultado.total is None
    assert resultado.interpretacion is None
    assert resultado.evidencias == ()
    assert resultado.error


def test_i35_identidad_vacia_falla_cerrada():
    resultado = evaluar_glasgow(4, 5, 6, valorado=True, id_valoracion="  ")
    assert not resultado.valorado
    assert resultado.evidencias == ()


def test_i36_total_es_derivacion_determinista_no_puntuable():
    total = valorar().evidencia_total
    assert total.naturaleza == NaturalezaEvidencia.DERIVACION_DETERMINISTA
    assert total.elegibilidad == ElegibilidadEvidencia.NO_PUNTUABLE
    assert not total.puntuable


def test_i37_interpretacion_es_separada_y_no_puntuable():
    resultado = valorar(1, 1, 6)
    evidencia = resultado.evidencia_interpretacion
    assert evidencia.naturaleza == NaturalezaEvidencia.INTERPRETACION
    assert evidencia.elegibilidad == ElegibilidadEvidencia.NO_PUNTUABLE
    assert evidencia not in resultado.evidencias[:4]
    assert not evidencia.puntuable


@pytest.mark.parametrize("total", [15, 14, 13, 12, 9, 8])
def test_i38_aislamientos_no_fabrican_hallazgos(total):
    combinaciones = [
        valores
        for valores in product(OPCIONES_OCULAR, OPCIONES_VERBAL, OPCIONES_MOTORA)
        if sum(valores) == total
    ]
    assert combinaciones
    for valores in combinaciones:
        resultado = valorar(*valores)
        assert resultado.total == total
        assert not (conceptos(resultado) & PROHIBIDOS)


def test_i38_total_ocho_con_v5_no_fabrica_alteracion_verbal():
    resultado = valorar(1, 5, 2)
    assert resultado.total == 8
    assert "respuesta verbal alterada" not in conceptos(resultado)


def test_i38_total_ocho_con_m6_no_fabrica_alteracion_motora():
    resultado = valorar(1, 1, 6)
    assert resultado.total == 8
    assert "respuesta motora alterada" not in conceptos(resultado)


def test_i39_i40_i41_componentes_no_tienen_mapeo_nanda_autorizado():
    resultado = valorar(4, 4, 6)
    for evidencia in resultado.evidencias:
        assert not evidencia.puntuable
    assert "confusión" not in conceptos(resultado)
    assert "respuesta verbal alterada" not in conceptos(resultado)


def test_i39_i44_evidencias_glasgow_no_puntuan_aunque_el_catalogo_coincidiera():
    fila_adversarial = {
        "nanda": "Diagnóstico adversarial",
        "caracteristicas": "respuesta ocular Glasgow;total Glasgow",
        "relacionados": "respuesta verbal Glasgow",
        "asociados": "respuesta motora Glasgow",
    }
    puntaje, coincidencias, _ = calcular_puntaje_evidencias(
        valorar(1, 2, 3).evidencias, fila_adversarial
    )
    assert puntaje == 0
    assert coincidencias == []


def test_i42_i48_alerta_no_afirma_datos_no_observados():
    texto = " ".join(
        valor
        for alerta in alertas_desde_glasgow(valorar(1, 1, 6))
        for valor in alerta.values()
    ).lower()
    for prohibido in PROHIBIDOS:
        assert prohibido not in texto
    assert "vía aérea" not in texto


def test_i43_glasgow_no_aporta_puntos_a_caidas_en_app():
    app = (RAIZ / "app.py").read_text(encoding="utf-8")
    assert "1 if glasgow_total < 15" not in app
    assert '("glasgow", hallazgos_glasgow)' not in app
    assert "hallazgos_glasgow" not in app


def test_i44_i45_glasgow_no_reinyecta_evidencias_en_fuentes_ajenas():
    app = (RAIZ / "app.py").read_text(encoding="utf-8")
    assert "evidencias_clinicas.extend(resultado_glasgow.evidencias)" not in app
    for evidencia in valorar().evidencias:
        assert evidencia.origen.startswith("glasgow.")


def test_i46_resumen_conserva_ovm_y_total():
    df = pd.DataFrame([{
        "Jerarquía": "Principal",
        "NANDA": "Diagnóstico educativo de prueba",
    }])
    resultado = valorar(3, 4, 5)
    resumen = generar_resumen_clinico(
        df, 23, "No valorado", 0, "No valorado",
        resultado.total, resultado.interpretacion,
        0, "No valorado", None, "No valorado", None, "No valorado", [],
        resultado_glasgow=resultado,
    )
    assert "O3, V4, M5" in resumen
    assert "total 12/15" in resumen


def test_i46_resumen_omite_glasgow_no_valorado():
    df = pd.DataFrame([{"Jerarquía": "Principal", "NANDA": "Prueba"}])
    resultado = evaluar_glasgow(4, 5, 6, valorado=False)
    resumen = generar_resumen_clinico(
        df, 23, "No valorado", 0, "No valorado",
        None, "No valorado", 0, "No valorado", None, "No valorado",
        None, "No valorado", [], resultado_glasgow=resultado,
    )
    assert "Glasgow" not in resumen


@pytest.mark.parametrize("total_legacy", [15, 8])
def test_p1b1_a2_resultado_no_valorado_prevalece_sobre_legacy(total_legacy):
    df = pd.DataFrame([{"Jerarquía": "Principal", "NANDA": "Prueba"}])
    resultado = evaluar_glasgow(4, 5, 6, valorado=False)
    resumen = generar_resumen_clinico(
        df, 23, "No valorado", 0, "No valorado",
        total_legacy, "Compromiso neurológico Legacy",
        0, "No valorado", None, "No valorado", None, "No valorado", [],
        resultado_glasgow=resultado,
    )
    assert "Glasgow" not in resumen


def test_p1b1_caso_a_desactivar_elimina_solo_alerta_glasgow_obsoleta():
    activo = valorar(1, 1, 6)
    alerta_ajena = {
        "Nivel": "Media",
        "Área": "Dolor",
        "Alerta": "Alerta no relacionada",
        "Acción sugerida": "Conservar",
    }
    almacenadas = alerta_ajena.copy(), *alertas_desde_glasgow(activo)
    omitido = evaluar_glasgow(4, 5, 6, valorado=False)
    sincronizadas = sincronizar_alertas_glasgow(list(almacenadas), omitido)
    assert sincronizadas == [alerta_ajena]
    assert not any(a.get("Origen") == "glasgow" for a in sincronizadas)


def test_p1b1_caso_b_cambiar_componentes_reemplaza_salidas_anteriores():
    anterior = valorar(1, 1, 6, episodio="episodio-activo")
    actual = valorar(4, 5, 6, episodio="episodio-activo")
    alertas = sincronizar_alertas_glasgow(alertas_desde_glasgow(anterior), actual)
    assert alertas == []

    datos = actualizar_datos_paciente_glasgow({"Edad": 40}, anterior)
    actualizados = actualizar_datos_paciente_glasgow(datos, actual)
    assert actualizados["Edad"] == 40
    assert actualizados["Glasgow ocular"] == "4 - Espontánea"
    assert actualizados["Glasgow verbal"] == "5 - Orientado"
    assert actualizados["Glasgow motora"] == "6 - Obedece órdenes"
    assert actualizados["Glasgow total"] == 15
    assert "1 - Sin respuesta" not in set(actualizados.values())


def test_p1b1_caso_c_reactivar_crea_id_nuevo_y_rerun_lo_conserva():
    primer_id = resolver_id_valoracion(
        valorado_actual=True, valorado_previo=False, id_actual=None
    )
    mismo_id = resolver_id_valoracion(
        valorado_actual=True, valorado_previo=True, id_actual=primer_id
    )
    desactivado = resolver_id_valoracion(
        valorado_actual=False, valorado_previo=True, id_actual=mismo_id
    )
    segundo_id = resolver_id_valoracion(
        valorado_actual=True, valorado_previo=False, id_actual=desactivado
    )
    assert mismo_id == primer_id
    assert desactivado is None
    assert segundo_id
    assert segundo_id != primer_id


def test_p1b1_caso_d_desactivar_limpia_solo_datos_exportables_glasgow():
    datos = actualizar_datos_paciente_glasgow(
        {"Edad": 40, "Diagnóstico médico": "Dato ajeno"},
        valorar(2, 3, 4),
    )
    omitido = evaluar_glasgow(4, 5, 6, valorado=False)
    actualizados = actualizar_datos_paciente_glasgow(datos, omitido)
    assert actualizados["Edad"] == 40
    assert actualizados["Diagnóstico médico"] == "Dato ajeno"
    assert {
        actualizados[campo]
        for campo in (
            "Glasgow valoración ID",
            "Glasgow ocular",
            "Glasgow verbal",
            "Glasgow motora",
            "Glasgow total",
            "Interpretación Glasgow",
        )
    } == {"No valorado"}


def test_i47_resultado_es_inmutable():
    resultado = valorar()
    with pytest.raises(Exception):
        resultado.total = 3


def test_i49_legacy_no_clasificado_permanece_fail_closed():
    evidencia = evidencia_estructurada(
        "disnea",
        fuente=FuenteEvidencia.OBSERVADO,
        origen="prueba_p1b",
        naturaleza=NaturalezaEvidencia.LEGACY_NO_CLASIFICADO,
        estado_validacion=EstadoValidacion.LEGACY,
        elegibilidad=ElegibilidadEvidencia.PUNTUABLE,
    )
    assert not evidencia.puntuable


def test_i50_scoring_permanece_intacto():
    assert SCORING_KIKE_NNN_V1 == {
        "DEF": 4,
        "REL": 2,
        "ASO": 1,
        "UMBRAL_VISIBILIDAD": 8,
    }
