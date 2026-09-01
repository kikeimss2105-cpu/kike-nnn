import pytest

from engine.carga import cargar_catalogos
from engine.evidencia import (
    ElegibilidadEvidencia,
    FuenteEvidencia,
    NaturalezaEvidencia,
    PolaridadEvidencia,
    evidencia_estructurada,
    evidencias_desde_eva,
    evidencias_desde_hallazgos,
)
from engine.motor import buscar_diagnosticos, calcular_puntaje, calcular_puntaje_evidencias
from engine.parser_negaciones import conceptos_catalogo, parsear_texto_libre


CAT = cargar_catalogos("data")
CONCEPTOS = conceptos_catalogo(CAT.nanda)


def parsear(texto):
    return parsear_texto_libre(texto, CONCEPTOS, origen="prueba").evidencias


def evidencia_por_concepto(texto, concepto):
    candidatas = [e for e in parsear(texto) if e.concepto == concepto]
    assert candidatas, f"No se extrajo {concepto!r} de {texto!r}"
    return candidatas[0]


@pytest.mark.parametrize("texto,concepto", [
    ("sin dolor", "dolor"),
    ("sin dolor agudo", "dolor agudo"),
    ("no presenta dolor", "dolor"),
    ("niega dolor", "dolor"),
    ("niega dolor agudo", "dolor agudo"),
    ("sin disnea", "disnea"),
    ("no presenta disnea", "disnea"),
    ("niega disnea", "disnea"),
    ("sin cianosis", "cianosis"),
    ("no presenta confusión", "confusion"),
    ("sin confusión", "confusion"),
    ("niega confusión", "confusion"),
    ("no presenta somnolencia", "somnolencia"),
    ("sin herida", "herida"),
    ("sin exudado", "exudado"),
    ("niega temor", "temor"),
    ("niega miedo", "miedo"),
    ("sin fiebre", "fiebre"),
    ("sin náusea", "nausea"),
    ("sin secreciones", "secreciones"),
    ("sin edema", "edema"),
])
def test_negaciones_directas_no_son_evidencia_positiva(texto, concepto):
    evidencia = evidencia_por_concepto(texto, concepto)
    assert evidencia.polaridad == PolaridadEvidencia.NEGADA
    assert not evidencia.puntuable
    assert buscar_diagnosticos(texto, CAT.nanda, CAT.enlaces).empty


@pytest.mark.parametrize("texto,esperados", [
    ("sin disnea ni cianosis", {"disnea", "cianosis"}),
    ("niega temor y miedo", {"temor", "miedo"}),
    ("no presenta confusión ni somnolencia", {"confusion", "somnolencia"}),
    ("sin herida ni exudado", {"herida", "exudado"}),
])
def test_coordinaciones_quedan_negadas(texto, esperados):
    evidencias = parsear(texto)
    assert {e.concepto for e in evidencias} == esperados
    assert all(e.polaridad == PolaridadEvidencia.NEGADA for e in evidencias)
    assert buscar_diagnosticos(texto, CAT.nanda, CAT.enlaces).empty


@pytest.mark.parametrize("texto,polaridades", [
    ("niega dolor pero presenta disnea", {"dolor": "NEGADA", "disnea": "POSITIVA"}),
    ("presenta dolor pero niega disnea", {"dolor": "POSITIVA", "disnea": "NEGADA"}),
    ("sin dolor, con náusea", {"dolor": "NEGADA", "nausea": "POSITIVA"}),
    ("sin fiebre pero presenta escalofríos", {"fiebre": "NEGADA", "escalofrios": "POSITIVA"}),
    ("niega sangrado, refiere dolor abdominal", {"sangrado": "NEGADA", "dolor abdominal": "POSITIVA"}),
    ("sin edema; presenta hipertensión", {"edema": "NEGADA", "hipertension": "POSITIVA"}),
])
def test_frases_mixtas_respetan_alcance(texto, polaridades):
    obtenidas = {e.concepto: e.polaridad.value for e in parsear(texto)}
    assert obtenidas == polaridades


@pytest.mark.parametrize("texto,concepto", [
    ("sin mejoría del dolor", "dolor"),
    ("sin control del dolor", "dolor"),
    ("no controla el dolor", "dolor"),
    ("sin respuesta al tratamiento del dolor", "dolor"),
    ("no disminuye el dolor", "dolor"),
    ("no puede dormir por dolor", "dolor"),
    ("no tolera alimentos por náusea", "nausea"),
    ("no logra expectorar secreciones", "secreciones"),
    ("sin control de la fiebre", "fiebre"),
])
def test_excepciones_no_niegan_el_concepto(texto, concepto):
    evidencia = evidencia_por_concepto(texto, concepto)
    assert evidencia.polaridad == PolaridadEvidencia.POSITIVA
    assert evidencia.puntuable


@pytest.mark.parametrize("texto,prohibido", [
    ("hipertensión", "tension"),
    ("respiratoria", "ira"),
    ("depresión", "presion"),
    ("preeclampsia", "eclampsia"),
    ("desprendimiento prematuro", "prematuro"),
])
def test_limites_lexicos_y_excepcion_contextual(texto, prohibido):
    assert prohibido not in {e.concepto for e in parsear(texto)}


def test_longest_match_first_no_duplica_dolor_agudo():
    evidencias = parsear("dolor agudo")
    assert [(e.concepto, e.inicio, e.fin) for e in evidencias] == [("dolor agudo", 0, 11)]


def test_api_legacy_calcular_puntaje_tambien_respeta_polaridad_y_limites():
    fila_dolor = CAT.nanda[CAT.nanda["codigo"] == "00132"].iloc[0]
    fila_temor = CAT.nanda[CAT.nanda["codigo"] == "00148"].iloc[0]
    assert calcular_puntaje("niega dolor agudo", fila_dolor) == (0, [])
    assert calcular_puntaje("hipertensión", fila_temor) == (0, [])


@pytest.mark.parametrize("texto,concepto", [
    ("dolor", "dolor"), ("dolor agudo", "dolor agudo"),
    ("presenta dolor", "dolor"), ("refiere dolor", "dolor"),
    ("disnea", "disnea"), ("presenta disnea", "disnea"),
    ("cianosis", "cianosis"), ("confusión", "confusion"),
    ("somnolencia", "somnolencia"), ("herida", "herida"),
    ("exudado", "exudado"), ("temor", "temor"), ("miedo", "miedo"),
    ("fiebre", "fiebre"), ("náusea", "nausea"),
    ("secreciones", "secreciones"), ("edema", "edema"),
])
def test_controles_positivos_se_conservan(texto, concepto):
    evidencia = evidencia_por_concepto(texto, concepto)
    assert evidencia.puntuable


@pytest.mark.parametrize("texto", [
    "no refiere dolor", "descarta dolor", "se descarta dolor",
    "posible dolor", "probable dolor", "dolor histórico",
    "dolor previo", "dolor resuelto",
])
def test_construcciones_no_soportadas_son_no_confiables(texto):
    evidencia = evidencia_por_concepto(texto, "dolor")
    assert evidencia.polaridad == PolaridadEvidencia.NO_CONFIABLE
    assert not evidencia.puntuable


def test_eva_positiva_y_dolor_negado_conservan_contradiccion():
    evidencias_eva = evidencias_desde_eva(8, valorado=True)
    evidencia_dolor = next(e for e in evidencias_eva if e.concepto == "dolor")
    evidencia_negada = next(e for e in parsear("niega dolor") if e.concepto == "dolor")

    assert evidencia_dolor.puntuable
    assert evidencia_negada.polaridad == PolaridadEvidencia.NEGADA
    assert not evidencia_negada.puntuable
    assert "dolor agudo" not in {e.concepto for e in evidencias_eva}

    evidencias = evidencias_eva + [evidencia_negada]
    resultado = buscar_diagnosticos("", CAT.nanda, CAT.enlaces, evidencias=evidencias)
    assert "dolor" in resultado.attrs["contradicciones"]
    assert resultado.attrs["advertencia_evidencia"] == (
        "Existen datos contradictorios que requieren revisión."
    )
    assert resultado.empty


@pytest.mark.parametrize("hallazgos,texto,concepto_negado", [
    (["saturación baja", "hipoxia", "deterioro del intercambio gaseoso", "cianosis", "oxigenación comprometida"], "niega disnea", None),
    (["confusión", "alteración del estado mental", "nivel de conciencia disminuido", "somnolencia", "deterioro neurológico"], "no presenta confusión", "confusion"),
    (["riesgo de lesión por presión", "inmovilidad", "humedad", "piel dañada", "fricción", "cizallamiento"], "sin lesión", None),
])
def test_legacy_no_puntua_y_texto_negado_no_crea_contradiccion(hallazgos, texto, concepto_negado):
    estructuradas = evidencias_desde_hallazgos(
        hallazgos,
        fuente=FuenteEvidencia.INFERIDO,
        origen="escala",
        derivada_de="escala_prueba",
    )
    solo_estructurado = buscar_diagnosticos("", CAT.nanda, CAT.enlaces, evidencias=estructuradas)
    combinado = buscar_diagnosticos(
        "", CAT.nanda, CAT.enlaces, evidencias=estructuradas + list(parsear(texto))
    )
    assert all(
        evidencia.naturaleza == NaturalezaEvidencia.LEGACY_NO_CLASIFICADO
        and not evidencia.puntuable
        for evidencia in estructuradas
    )
    assert list(solo_estructurado.get("Código", [])) == list(combinado.get("Código", []))
    assert list(solo_estructurado.get("Puntaje", [])) == list(combinado.get("Puntaje", []))
    if concepto_negado:
        evidencia_negada = next(
            evidencia for evidencia in parsear(texto)
            if evidencia.concepto == concepto_negado
        )
        assert evidencia_negada.polaridad == PolaridadEvidencia.NEGADA
        assert concepto_negado not in combinado.attrs["contradicciones"]


def test_coincidencia_conserva_trazabilidad_estructurada():
    evidencias = evidencias_desde_hallazgos(
        ["dolor", "dolor agudo"],
        fuente=FuenteEvidencia.MEDIDO,
        origen="eva",
        derivada_de="eva_dolor",
    )
    fila_dolor = CAT.nanda[CAT.nanda["codigo"] == "00132"].iloc[0]
    puntaje, coincidencias, detalles = calcular_puntaje_evidencias(evidencias, fila_dolor)
    detalle_autorreferencia = next(
        d for d in detalles
        if d["elegibilidad"] == ElegibilidadEvidencia.PROHIBIDA_AUTORREFERENCIA.value
    )

    assert {evidencia.concepto for evidencia in evidencias} == {"dolor", "dolor agudo"}
    assert all(
        evidencia.naturaleza == NaturalezaEvidencia.LEGACY_NO_CLASIFICADO
        and not evidencia.puntuable
        for evidencia in evidencias
    )
    assert {evidencia.fuente for evidencia in evidencias} == {FuenteEvidencia.MEDIDO}
    assert {evidencia.origen for evidencia in evidencias} == {"eva"}
    assert {evidencia.derivada_de for evidencia in evidencias} == {"eva_dolor"}
    assert coincidencias == []
    assert puntaje == 0
    assert puntaje < 8
    assert detalle_autorreferencia["termino"] == "dolor agudo"
    assert detalle_autorreferencia["categoria"] == "AUTORREFERENCIA"
    assert {d["fuente"] for d in detalles} == {"MEDIDO"}
    assert {d["origen"] for d in detalles} == {"eva"}
    assert {d["derivada_de"] for d in detalles} == {"eva_dolor"}

    resultado = buscar_diagnosticos("", CAT.nanda, CAT.enlaces, evidencias=evidencias)
    assert resultado.empty
    assert resultado.attrs["autorreferencias_prohibidas"]


def test_fallo_parser_es_no_confiable_y_no_genera_evidencia():
    class ConceptosRotos:
        def __iter__(self):
            raise RuntimeError("fallo controlado")

    resultado = parsear_texto_libre("dolor", ConceptosRotos())
    assert resultado.estado == "PARSING_NO_CONFIABLE"
    assert resultado.evidencias == ()
