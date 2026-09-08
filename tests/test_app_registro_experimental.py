"""El registro se descarga desde el flujo real, incluso sin sugerencias."""
import pandas as pd
from streamlit.testing.v1 import AppTest
from test_app_estado_valoracion import APP, ejecutar, iniciar, generar, widget
from test_app_intentos import responder
from engine.registro_experimental import construir_registro, recuperar_registro, serializar_registro


def activar(app, participante="P001", momento="PRE"):
    widget(app, "text_input", "Código seudónimo del participante").set_value(participante)
    widget(app, "selectbox", "Momento experimental").set_value(momento)
    widget(app, "button", "Iniciar sesión experimental").click()
    ejecutar(app)


def actual(app):
    return construir_registro(app.session_state.experimental_sesion, app.session_state.filtered_state, app.session_state.valoracion_generada)


def test_ui_identidad_y_dos_intentos_sin_mezcla():
    app = iniciar()
    activar(app)
    sesion = app.session_state.experimental_sesion
    generar(app)
    responder(app)
    primero = actual(app)
    generar(app)
    segundo = actual(app)
    assert app.session_state.experimental_sesion == sesion
    assert primero["participante_id"] == segundo["participante_id"] == "P001"
    assert primero["intento_id"] != segundo["intento_id"]
    assert all(a == "" for a in segundo["argumentos"].values())
    assert recuperar_registro(serializar_registro(primero)) == primero
    widget(app, "number_input", "SpO₂ (%)").set_value(80)
    ejecutar(app)
    assert not app.get("download_button")


def test_ui_cero_sugerencias_descargable(monkeypatch):
    import engine.motor
    monkeypatch.setattr(engine.motor, "buscar_diagnosticos", lambda *a, **kw: pd.DataFrame())
    app = iniciar()
    activar(app)
    generar(app)
    assert app.session_state.df_resultados.empty
    r = actual(app)
    assert r["estado"] == "COMPLETADO" and r["sugerencias"] == []
    assert len(app.get("download_button")) == 1
    assert app.get("download_button")[0].label == "Descargar registro experimental JSON"


def test_ui_nueva_sesion_limpia_resultados_y_otro_participante():
    app = iniciar()
    activar(app)
    generar(app)
    anterior = app.session_state.experimental_sesion
    widget(app, "button", "Preparar otra sesión experimental").click()
    ejecutar(app)
    activar(app, "P002", "POST")
    assert "intento_id" not in app.session_state
    assert "justificaciones" not in app.session_state
    assert app.session_state.experimental_sesion.sesion_id != anterior.sesion_id
    generar(app)
    assert actual(app)["participante_id"] == "P002"


def test_ui_fallo_no_reutiliza_resultados_y_recupera(monkeypatch):
    import engine.motor
    app = iniciar()
    activar(app)
    generar(app)
    responder(app)
    original = engine.motor.buscar_diagnosticos
    def fallar(*args, **kwargs):
        raise RuntimeError("No guardar mensajes potencialmente sensibles")
    monkeypatch.setattr(engine.motor, "buscar_diagnosticos", fallar)
    widget(app, "button", "🩺 Generar Plan de Cuidados").click()
    ejecutar(app)
    r = actual(app)
    assert r["estado"] == "FALLO"
    assert r["intento_id"] is None and r["sugerencias"] == [] and r["argumentos"] == {}
    assert "sensibles" not in serializar_registro(r).decode()
    assert len(app.get("download_button")) == 1
    monkeypatch.setattr(engine.motor, "buscar_diagnosticos", original)
    generar(app)
    assert actual(app)["estado"] == "INCOMPLETO"


def test_ui_iniciar_sin_generar_y_validacion():
    app = ejecutar(AppTest.from_file(str(APP), default_timeout=30))
    app.button[0].click()
    ejecutar(app)
    activar(app, "", "PRE")
    assert "experimental_sesion" not in app.session_state
    assert not app.get("download_button")
    activar(app)
    assert len(app.get("download_button")) == 1
