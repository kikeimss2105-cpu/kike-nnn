import pytest

from engine.carga import cargar_catalogos
from engine.evidencia import (
    ConfiabilidadEvidencia,
    ElegibilidadEvidencia,
    EstadoValidacion,
    FuenteEvidencia,
    NaturalezaEvidencia,
    PolaridadEvidencia,
    evidencia_estructurada,
)
from engine.motor import calcular_puntaje_evidencias
from engine.parser_negaciones import conceptos_catalogo, etiquetas_nanda, parsear_texto_libre


CAT = cargar_catalogos("data")
FILA = CAT.nanda[CAT.nanda["codigo"] == "00032"].iloc[0]


def candidata(
    concepto="disnea",
    *,
    naturaleza=NaturalezaEvidencia.DATO_PRIMARIO_OBSERVADO,
    fuente=FuenteEvidencia.OBSERVADO,
    estado=EstadoValidacion.VALIDADO,
    elegibilidad=ElegibilidadEvidencia.PUNTUABLE,
    derivada_de=None,
    id_dato_primario=None,
):
    return evidencia_estructurada(
        concepto,
        fuente=fuente,
        origen="prueba_p1a",
        derivada_de=derivada_de,
        id_dato_primario=id_dato_primario,
        naturaleza=naturaleza,
        estado_validacion=estado,
        elegibilidad=elegibilidad,
    )


def puntaje(evidencia):
    return calcular_puntaje_evidencias([evidencia], FILA)[0]


def test_i21_i28_legacy_es_fail_closed_aunque_declare_puntuable():
    evidencia = candidata(naturaleza=NaturalezaEvidencia.LEGACY_NO_CLASIFICADO)
    assert not evidencia.puntuable
    assert puntaje(evidencia) == 0


@pytest.mark.parametrize("naturaleza", [
    NaturalezaEvidencia.CONCLUSION_DIAGNOSTICA,
    NaturalezaEvidencia.INTERPRETACION,
    NaturalezaEvidencia.CONTEXTO,
    NaturalezaEvidencia.ALERTA,
    NaturalezaEvidencia.SALIDA_SISTEMA,
])
def test_i22_i23_naturalezas_no_clinicas_nunca_puntuan(naturaleza):
    evidencia = candidata(naturaleza=naturaleza)
    assert not evidencia.puntuable
    assert puntaje(evidencia) == 0


def test_i24_derivacion_pendiente_no_puntua():
    evidencia = candidata(
        naturaleza=NaturalezaEvidencia.DERIVACION_DETERMINISTA,
        estado=EstadoValidacion.PENDIENTE_VALIDACION,
        derivada_de="dato-1",
    )
    assert puntaje(evidencia) == 0


def test_i24_derivacion_validada_sin_progenitor_no_puntua():
    evidencia = candidata(naturaleza=NaturalezaEvidencia.DERIVACION_DETERMINISTA)
    assert puntaje(evidencia) == 0


def test_i24_derivacion_validada_con_progenitor_y_elegibilidad_puede_puntuar():
    evidencia = candidata(
        naturaleza=NaturalezaEvidencia.DERIVACION_DETERMINISTA,
        derivada_de="dato-1",
    )
    assert evidencia.puntuable
    assert puntaje(evidencia) == 4


def test_i25_observacion_estructurada_legacy_sin_id_conserva_compatibilidad():
    evidencia = candidata()
    assert evidencia.puntuable
    assert puntaje(evidencia) == 4


def test_i25_dato_referido_legitimo_conserva_puntuacion():
    evidencia = candidata(
        fuente=FuenteEvidencia.REFERIDO_ESTRUCTURADO,
        naturaleza=NaturalezaEvidencia.DATO_PRIMARIO_REFERIDO,
    )
    assert evidencia.puntuable
    assert puntaje(evidencia) == 4


def test_i26_etiqueta_nanda_en_texto_es_conclusion_y_no_puntua():
    resultado = parsear_texto_libre(
        "Patrón respiratorio ineficaz",
        conceptos_catalogo(CAT.nanda),
        origen="prueba_p1a",
        conclusiones_diagnosticas=etiquetas_nanda(CAT.nanda),
    )
    [evidencia] = resultado.evidencias
    assert evidencia.naturaleza == NaturalezaEvidencia.CONCLUSION_DIAGNOSTICA
    assert evidencia.elegibilidad == ElegibilidadEvidencia.NO_PUNTUABLE
    assert puntaje(evidencia) == 0


def test_i27_motor_rechaza_conclusion_mal_marcada_como_puntuable():
    evidencia = candidata(naturaleza=NaturalezaEvidencia.CONCLUSION_DIAGNOSTICA)
    assert calcular_puntaje_evidencias([evidencia], FILA)[0] == 0


@pytest.mark.parametrize("polaridad,confiabilidad", [
    (PolaridadEvidencia.NEGADA, ConfiabilidadEvidencia.CONFIABLE),
    (PolaridadEvidencia.INCIERTA, ConfiabilidadEvidencia.CONFIABLE),
    (PolaridadEvidencia.NO_CONFIABLE, ConfiabilidadEvidencia.NO_CONFIABLE),
])
def test_polaridad_o_confiabilidad_insegura_continua_sin_puntuar(
    polaridad, confiabilidad
):
    base = candidata()
    evidencia = type(base)(
        **{
            **base.__dict__,
            "polaridad": polaridad,
            "confiabilidad": confiabilidad,
        }
    )
    assert not evidencia.puntuable
    assert puntaje(evidencia) == 0


def test_autorreferencia_p0_continua_bloqueada():
    evidencia = candidata("Patrón respiratorio ineficaz")
    puntaje_real, coincidencias, detalles = calcular_puntaje_evidencias([evidencia], FILA)
    assert puntaje_real == 0
    assert coincidencias == []
    assert detalles[0]["elegibilidad"] == "PROHIBIDA_AUTORREFERENCIA"
