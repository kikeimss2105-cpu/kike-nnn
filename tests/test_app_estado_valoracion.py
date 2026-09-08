"""Regresiones del vínculo entre valoración y resultados en Streamlit."""

from copy import deepcopy
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from utils import exportadores


APP = Path(__file__).resolve().parents[1] / "app.py"


def widget(app, tipo, etiqueta):
    return next(w for w in getattr(app, tipo) if w.label == etiqueta)


def ejecutar(app):
    app.run()
    assert not app.exception
    return app


def generar(app):
    widget(app, "button", "🩺 Generar Plan de Cuidados").click()
    ejecutar(app)
    assert app.session_state.plan_generado
    assert not app.session_state.resultados_invalidados


def iniciar():
    app = ejecutar(AppTest.from_file(str(APP), default_timeout=30))
    app.button[0].click()
    ejecutar(app)
    for etiqueta in ("Disnea", "Cianosis", "Hipoxia"):
        widget(app, "checkbox", etiqueta).check()
    widget(app, "toggle", "✅ Incluir módulo respiratorio en la valoración").set_value(True)
    ejecutar(app)
    return app


@pytest.fixture
def exportaciones(monkeypatch):
    llamadas = []
    for nombre in ("generar_excel", "generar_word", "generar_word_docente"):
        original = getattr(exportadores, nombre)

        def registrar(df, datos, *args, _original=original, _nombre=nombre):
            llamadas.append((_nombre, deepcopy(datos), df.to_dict("records")))
            return _original(df, datos, *args)

        monkeypatch.setattr(exportadores, nombre, registrar)
    return llamadas


def comprobar_invalidacion(app):
    assert not app.session_state.plan_generado
    assert app.session_state.resultados_invalidados
    for clave in ("df_resultados", "datos_paciente", "alertas_clinicas", "valoracion_generada"):
        assert clave not in app.session_state
    assert any("La valoración cambió" in w.value for w in app.warning)
    assert not app.get("download_button")
    assert not app.dataframe
    assert not any("Resumen clínico educativo" in h.value for h in app.subheader)
    assert not any("Plan narrativo" in h.value for h in app.subheader)


@pytest.mark.parametrize("tipo,etiqueta,valor", [
    ("number_input", "SpO₂ (%)", 80),
    ("selectbox", "Tipo de paciente", "Obstétrico"),
    ("checkbox", "Disnea", False),
    ("text_area", "Síntomas, hallazgos y datos relevantes en texto libre", "sin disnea"),
    ("number_input", "Frecuencia respiratoria (rpm)", 32),
    ("toggle", "✅ Incluir módulo respiratorio en la valoración", False),
])
def test_cambio_invalida_sin_exportar_y_regeneracion_es_coherente(
    tipo, etiqueta, valor, exportaciones,
):
    app = iniciar()
    generar(app)
    assert len(app.get("download_button")) == 3
    exportaciones.clear()

    widget(app, tipo, etiqueta).set_value(valor)
    ejecutar(app)
    comprobar_invalidacion(app)
    ejecutar(app)
    comprobar_invalidacion(app)
    assert exportaciones == []

    generar(app)
    assert len(app.get("download_button")) == 3
    assert not any("La valoración cambió" in w.value for w in app.warning)
    assert len(exportaciones) == 3
    for _, datos, sugerencias in exportaciones:
        assert datos == app.session_state.datos_paciente
        assert sugerencias == app.session_state.df_resultados.to_dict("records")

    # Un arranque independiente con las mismas entradas debe producir el
    # mismo conjunto, sin restos de la primera generación.
    nueva = iniciar()
    widget(nueva, tipo, etiqueta).set_value(valor)
    ejecutar(nueva)
    generar(nueva)
    assert app.session_state.datos_paciente == nueva.session_state.datos_paciente
    assert app.session_state.alertas_clinicas == nueva.session_state.alertas_clinicas
    assert app.session_state.df_resultados.to_dict("records") == nueva.session_state.df_resultados.to_dict("records")
    if etiqueta == "SpO₂ (%)":
        assert app.session_state.datos_paciente["SpO2 (%)"] == 80
        assert "SpO₂ 80%" in app.session_state.datos_paciente["Resumen clínico educativo"]
        assert any("SpO₂ 80%" in a["Alerta"] for a in app.session_state.alertas_clinicas)


def test_sin_cambios_y_justificaciones_no_invalidan():
    app = iniciar()
    generar(app)
    datos = deepcopy(app.session_state.datos_paciente)
    ejecutar(app)  # Un rerun sin cambios de valoración no invalida.
    assert app.session_state.plan_generado
    app.radio[0].set_value("Aceptado")
    ejecutar(app)
    next(w for w in app.text_area if w.key and w.key.endswith("_texto")).set_value("Argumento")
    ejecutar(app)
    assert app.session_state.plan_generado
    assert app.session_state.datos_paciente == datos
    assert len(app.get("download_button")) == 3


@pytest.mark.parametrize("perfil,tipo,etiqueta,valor", [
    ("Adulto", "number_input", "Edad", 40),
    ("Adulto", "toggle", "✅ Incluir Braden en la valoración", True),
    ("Adulto", "toggle", "✅ Incluir EVA en la valoración", True),
    ("Adulto", "checkbox", "Caída previa reciente", True),
    ("Adulto", "checkbox", "¿Edema presente?", True),
    ("Obstétrico", "number_input", "Presión sistólica (mmHg)", 160),
    ("Recién nacido", "selectbox", "Apariencia", 1),
    ("Recién nacido", "radio", "Variante", "B"),
])
def test_otras_entradas_de_valoracion_invalidan(perfil, tipo, etiqueta, valor):
    app = iniciar()
    widget(app, "selectbox", "Tipo de paciente").set_value(perfil)
    if etiqueta == "Caída previa reciente":
        widget(app, "toggle", "✅ Incluir tamizaje de caídas en la valoración").set_value(True)
    ejecutar(app)
    generar(app)
    widget(app, tipo, etiqueta).set_value(valor)
    ejecutar(app)
    comprobar_invalidacion(app)


def test_glasgow_invalida_y_conserva_identidad_y_no_valorado():
    app = iniciar()
    etiqueta = "✅ Incluir Glasgow en la valoración"
    widget(app, "toggle", etiqueta).set_value(True)
    ejecutar(app)
    generar(app)
    identidad = app.session_state.datos_paciente["Glasgow valoración ID"]
    widget(app, "selectbox", "Respuesta ocular").set_value(1)
    ejecutar(app)
    comprobar_invalidacion(app)
    generar(app)
    assert app.session_state.datos_paciente["Glasgow total"] == 12
    assert app.session_state.datos_paciente["Glasgow valoración ID"] == identidad
    assert any(a.get("Origen") == "glasgow" for a in app.session_state.alertas_clinicas)
    widget(app, "toggle", etiqueta).set_value(False)
    ejecutar(app)
    comprobar_invalidacion(app)
    generar(app)
    assert app.session_state.datos_paciente["Glasgow total"] == "No valorado"
    assert not any(a.get("Origen") == "glasgow" for a in app.session_state.alertas_clinicas)


def test_plan_sin_snapshot_no_se_considera_valido():
    app = iniciar()
    generar(app)
    del app.session_state["valoracion_generada"]
    ejecutar(app)
    comprobar_invalidacion(app)


def test_braden_inactivo_no_invalida_pero_componentes_activos_si():
    app = iniciar()
    generar(app)
    assert widget(app, "selectbox", "Percepción sensorial").disabled
    ejecutar(app)
    assert app.session_state.plan_generado
    widget(app, "toggle", "✅ Incluir Braden en la valoración").set_value(True)
    ejecutar(app)
    widget(app, "selectbox", "Percepción sensorial").set_value(3)
    ejecutar(app)
    generar(app)
    # Mismo total, componentes distintos: no basta comparar el puntaje.
    widget(app, "selectbox", "Percepción sensorial").set_value(4)
    widget(app, "selectbox", "Humedad").set_value(3)
    ejecutar(app)
    comprobar_invalidacion(app)
