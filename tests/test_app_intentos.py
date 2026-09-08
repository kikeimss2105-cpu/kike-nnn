"""Las respuestas pertenecen a una generación, no solo al diagnóstico."""

from copy import deepcopy

from test_app_estado_valoracion import (
    comprobar_invalidacion,
    ejecutar,
    generar,
    iniciar,
    widget,
)
from utils import exportadores


def responder(app, decision="Aceptado", argumento="Argumento del primer intento"):
    fila = app.session_state.df_resultados.iloc[0]
    base = f"justif_{app.session_state.intento_id}_{fila['Código']}"
    app.radio(key=f"{base}_decision").set_value(decision)
    criterios = app.multiselect(key=f"{base}_criterios")
    criterios.set_value([criterios.options[0]])
    app.text_area(key=f"{base}_texto").set_value(argumento)
    ejecutar(app)
    respuesta = app.session_state.justificaciones[fila["NANDA"]]
    assert respuesta["decision"] == decision
    assert respuesta["criterios"]
    assert respuesta["justificacion"] == argumento
    return fila["Código"]


def comprobar_intento_limpio(app, anterior, codigo):
    assert app.session_state.intento_id != anterior
    assert codigo in app.session_state.df_resultados["Código"].tolist()
    for respuesta in app.session_state.justificaciones.values():
        assert respuesta["decision"] == "Sin decidir"
        assert respuesta["criterios"] == []
        assert respuesta["justificacion"] == ""
    assert all(w.value == "Sin decidir" for w in app.radio)
    assert all(w.value == [] for w in app.multiselect)
    assert all(w.value == "" for w in app.text_area if w.key and w.key.startswith("justif_"))
    assert not any(k.startswith(f"justif_{anterior}_") for k in app.session_state.filtered_state)


def test_regenerar_mismo_diagnostico_limpia_widgets_y_exportaciones(monkeypatch):
    exportadas = []
    for nombre in ("generar_excel", "generar_word", "generar_word_docente"):
        original = getattr(exportadores, nombre)

        def registrar(df, datos, respuestas, *args, _original=original):
            exportadas.append(deepcopy(respuestas))
            return _original(df, datos, respuestas, *args)

        monkeypatch.setattr(exportadores, nombre, registrar)
    app = iniciar()
    generar(app)
    anterior = app.session_state.intento_id
    codigo = responder(app)
    exportadas.clear()
    generar(app)
    comprobar_intento_limpio(app, anterior, codigo)
    assert len(exportadas) == 3
    assert all(respuestas == app.session_state.justificaciones for respuestas in exportadas)


def test_reruns_y_edicion_conservan_respuestas_del_intento_actual():
    app = iniciar()
    generar(app)
    identidad = app.session_state.intento_id
    responder(app)
    respuestas = deepcopy(app.session_state.justificaciones)
    valoracion = deepcopy(app.session_state.valoracion_generada)
    for _ in range(2):
        ejecutar(app)
        assert app.session_state.intento_id == identidad
        assert app.session_state.justificaciones == respuestas
        assert app.session_state.valoracion_generada == valoracion
        assert app.session_state.plan_generado
    responder(app, "Rechazado", "Argumento revisado dentro del mismo intento")
    assert app.session_state.intento_id == identidad


def test_invalidar_y_regenerar_abre_intento_limpio():
    app = iniciar()
    generar(app)
    anterior = app.session_state.intento_id
    codigo = responder(app)
    widget(app, "number_input", "SpO₂ (%)").set_value(80)
    ejecutar(app)
    comprobar_invalidacion(app)
    generar(app)
    comprobar_intento_limpio(app, anterior, codigo)
    assert app.session_state.datos_paciente["SpO2 (%)"] == 80


def test_dos_regeneraciones_consecutivas_aislan_tres_intentos():
    app = iniciar()
    generar(app)
    identidades = {app.session_state.intento_id}
    for decision, argumento in (("Aceptado", "Respuesta uno"), ("Rechazado", "Respuesta dos")):
        anterior = app.session_state.intento_id
        codigo = responder(app, decision, argumento)
        generar(app)
        comprobar_intento_limpio(app, anterior, codigo)
        assert app.session_state.intento_id not in identidades
        identidades.add(app.session_state.intento_id)
    assert len(identidades) == 3
