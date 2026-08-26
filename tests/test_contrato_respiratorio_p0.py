from pathlib import Path

import pytest

from engine.carga import cargar_catalogos
from engine.evidencia import (
    ConfiabilidadEvidencia,
    ElegibilidadEvidencia,
    EstadoValidacion,
    EvidenciaClinica,
    FuenteEvidencia,
    NaturalezaEvidencia,
    PolaridadEvidencia,
    evidencias_desde_eva,
)
from engine.interpretaciones import interpretar_fr_por_tipo
from engine.motor import calcular_puntaje_evidencias
from engine.parser_negaciones import conceptos_catalogo, parsear_texto_libre
from engine.respiratorio import (
    evaluar_fr,
    evidencias_desde_resultado_fr,
    evidencias_desde_spo2,
)
from engine.resumen import generar_alertas_clinicas


CAT = cargar_catalogos("data")
FILA_PATRON = CAT.nanda[CAT.nanda["codigo"] == "00032"].iloc[0]


def resultado_fr(valor=35, **cambios):
    parametros = {
        "valorado": True,
        "perfil": "Adulto",
        "edad": 40,
        "contexto_obstetrico": {"aplica": False},
        "origen": "prueba.fr",
        "id_dato_primario": "fr-1",
    }
    parametros.update(cambios)
    return evaluar_fr(valor, **parametros)


def evidencia(
    concepto,
    *,
    naturaleza=NaturalezaEvidencia.DATO_PRIMARIO_OBSERVADO,
    estado=EstadoValidacion.VALIDADO,
    elegibilidad=ElegibilidadEvidencia.PUNTUABLE,
    polaridad=PolaridadEvidencia.POSITIVA,
    confiabilidad=ConfiabilidadEvidencia.CONFIABLE,
):
    return EvidenciaClinica(
        concepto=concepto,
        texto_original=concepto,
        fuente=FuenteEvidencia.OBSERVADO,
        polaridad=polaridad,
        confiabilidad=confiabilidad,
        origen="prueba",
        naturaleza=naturaleza,
        estado_validacion=estado,
        elegibilidad=elegibilidad,
    )


def test_i01_fr_no_valorada_no_produce_evidencia_derivada():
    resultado = resultado_fr(None, valorado=False)
    assert resultado.valor_rpm is None
    assert resultado.clasificacion is None
    assert resultado.alerta is None
    assert evidencias_desde_resultado_fr(resultado) == []


@pytest.mark.parametrize("prohibido", [
    "uso de músculos accesorios",
    "fatiga de músculos respiratorios",
    "patrón respiratorio ineficaz",
])
def test_i02_i03_i04_fr_sola_no_infiere_signos_ni_nanda(prohibido):
    conceptos = {e.concepto for e in evidencias_desde_resultado_fr(resultado_fr())}
    assert prohibido not in conceptos


def test_i05_spo2_sola_no_genera_cianosis():
    conceptos = {
        e.concepto for e in evidencias_desde_spo2(
            80, valorado=True, id_dato_primario="spo2-1"
        )
    }
    assert "cianosis" not in conceptos


def test_i06_eva_sola_no_genera_punzada_ni_dolor_agudo():
    conceptos = {e.concepto for e in evidencias_desde_eva(10, valorado=True)}
    assert "punzada" not in conceptos
    assert "dolor agudo" not in conceptos


def test_i07_etiqueta_nanda_igual_a_evidencia_aporta_cero():
    puntaje, coincidencias, detalles = calcular_puntaje_evidencias(
        [evidencia("Patrón respiratorio ineficaz")], FILA_PATRON
    )
    assert puntaje == 0
    assert coincidencias == []
    assert detalles[0]["elegibilidad"] == "PROHIBIDA_AUTORREFERENCIA"


def test_i08_fr_y_spo2_conservan_ids_primarios_distintos():
    fr = evidencias_desde_resultado_fr(resultado_fr())
    spo2 = evidencias_desde_spo2(90, valorado=True, id_dato_primario="spo2-1")
    assert fr[0].id_dato_primario == "fr-1"
    assert spo2[0].id_dato_primario == "spo2-1"
    assert fr[0].id_dato_primario != spo2[0].id_dato_primario


def test_i09_derivacion_conserva_progenitor():
    derivadas = [
        e for e in evidencias_desde_resultado_fr(resultado_fr())
        if e.naturaleza == NaturalezaEvidencia.DERIVACION_DETERMINISTA
    ]
    assert derivadas
    assert {e.derivada_de for e in derivadas} == {"fr-1"}


def test_i10_pendiente_validacion_no_puntua():
    candidata = evidencia("taquipnea", estado=EstadoValidacion.PENDIENTE_VALIDACION)
    assert not candidata.puntuable
    assert calcular_puntaje_evidencias([candidata], FILA_PATRON)[0] == 0


@pytest.mark.parametrize("naturaleza", [
    NaturalezaEvidencia.INTERPRETACION,
    NaturalezaEvidencia.CONCLUSION_DIAGNOSTICA,
])
def test_i11_i12_interpretacion_y_conclusion_no_puntuan(naturaleza):
    candidata = evidencia("taquipnea", naturaleza=naturaleza)
    assert not candidata.puntuable
    assert calcular_puntaje_evidencias([candidata], FILA_PATRON)[0] == 0


def test_i13_dato_observado_positivo_confiable_conserva_elegibilidad():
    candidata = evidencia("disnea")
    assert candidata.puntuable
    assert calcular_puntaje_evidencias([candidata], FILA_PATRON)[0] == 4


def test_i14_negacion_aporta_cero():
    conceptos = conceptos_catalogo(CAT.nanda)
    resultado = parsear_texto_libre("niega disnea", conceptos, origen="prueba")
    assert not resultado.evidencias[0].puntuable
    assert calcular_puntaje_evidencias(resultado.evidencias, FILA_PATRON)[0] == 0


@pytest.mark.parametrize("candidata", [
    evidencia("disnea", polaridad=PolaridadEvidencia.INCIERTA),
    evidencia(
        "disnea",
        polaridad=PolaridadEvidencia.NO_CONFIABLE,
        confiabilidad=ConfiabilidadEvidencia.NO_CONFIABLE,
    ),
])
def test_i15_incierto_o_no_confiable_aporta_cero(candidata):
    assert not candidata.puntuable
    assert calcular_puntaje_evidencias([candidata], FILA_PATRON)[0] == 0


def test_i16_ui_y_alertas_consumen_el_mismo_resultado_fr():
    resultado = resultado_fr(45, perfil="Pediátrico")
    assert interpretar_fr_por_tipo(45, "Pediátrico") == resultado.interpretacion
    alertas = generar_alertas_clinicas(
        spo2=None,
        fr=resultado.valor_rpm,
        eva_dolor=0,
        puntaje_braden=23,
        glasgow_total=15,
        puntaje_caidas=0,
        riesgo_caidas="No valorado",
        hallazgos_seleccionados=[],
        resultado_fr=resultado,
    )
    assert alertas[0]["Alerta"] == resultado.alerta.mensaje
    assert alertas[0]["Regla FR"] == resultado.regla_id
    assert alertas[0]["Dato primario FR"] == resultado.id_dato_primario


def test_i17_consumidores_no_recalculan_umbrales_fr():
    raiz = Path(__file__).resolve().parents[1]
    for ruta in (raiz / "app.py", raiz / "engine" / "resumen.py", raiz / "engine" / "interpretaciones.py"):
        texto = ruta.read_text(encoding="utf-8")
        assert "fr >" not in texto.lower()
        assert "fr <" not in texto.lower()


def test_i18_edad_se_preserva():
    assert resultado_fr(24, edad=73).edad == 73


def test_i19_contexto_y_perfil_se_preservan():
    contexto = {"semanas_gestacion": 30}
    resultado = resultado_fr(24, perfil="Obstétrico", contexto_obstetrico=contexto)
    assert resultado.perfil == "Obstétrico"
    assert resultado.contexto_obstetrico == contexto


def test_i20_no_hay_fallback_adulto_silencioso():
    resultado = resultado_fr(21, perfil="Perfil desconocido")
    assert resultado.clasificacion is None
    assert resultado.interpretacion is None
    assert resultado.alerta is None
    assert resultado.error == "Perfil respiratorio no reconocido."
    assert interpretar_fr_por_tipo(21, "Perfil desconocido") is None
