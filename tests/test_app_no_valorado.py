"""Escalas desactivadas no describen observaciones ni normalidad."""

import pytest

from test_app_estado_valoracion import (
    comprobar_invalidacion, ejecutar, exportaciones, generar, iniciar, widget,
)


ESCALAS = [
    ("Braden", "✅ Incluir Braden en la valoración", "selectbox",
     "Percepción sensorial", 1, "Puntaje Braden", "Interpretación Braden",
     "Braden: No valorado", "Escala de Braden:"),
    ("EVA", "✅ Incluir EVA en la valoración", "slider",
     "Intensidad del dolor", 8, "EVA dolor", "Interpretación EVA",
     "EVA: No valorado", "EVA del dolor:"),
    ("caídas", "✅ Incluir tamizaje de caídas en la valoración", "checkbox",
     "Confusión o desorientación", True, "Puntaje riesgo de caídas",
     "Interpretación riesgo de caídas", "Riesgo de caídas: No valorado", "Riesgo de caídas:"),
]


@pytest.mark.parametrize("escala,toggle,tipo,control,valor,puntaje,interpretacion,aviso,resumen", ESCALAS)
def test_no_valorado_no_muestra_interpretacion(
    escala, toggle, tipo, control, valor, puntaje, interpretacion, aviso, resumen,
):
    app = iniciar()
    assert widget(app, tipo, control).disabled
    assert aviso in [i.value for i in app.info]
    generar(app)
    assert app.session_state.datos_paciente[puntaje] == "No valorado"
    assert app.session_state.datos_paciente[interpretacion] == "No valorado"
    assert resumen not in app.session_state.datos_paciente["Resumen clínico educativo"]
    assert not any("Sin dolor" in i.value or "Sin riesgo significativo" in i.value for i in app.info)


@pytest.mark.parametrize("escala,toggle,tipo,control,valor,puntaje,interpretacion,aviso,resumen", ESCALAS)
def test_desactivar_excluye_valores_previos_y_reactivar_permite_valorar(
    escala, toggle, tipo, control, valor, puntaje, interpretacion, aviso, resumen,
    exportaciones,
):
    app = iniciar()
    generar(app)
    iniciales = app.session_state.datos_paciente["Hallazgos estructurados"]
    widget(app, "toggle", toggle).set_value(True)
    ejecutar(app)
    widget(app, tipo, control).set_value(valor)
    if escala == "Braden":
        for etiqueta in ("Humedad", "Actividad", "Movilidad", "Nutrición", "Fricción y cizallamiento"):
            widget(app, "selectbox", etiqueta).set_value(1)
    elif escala == "caídas":
        for etiqueta in ("Caída previa reciente", "Marcha inestable o alterada"):
            widget(app, "checkbox", etiqueta).set_value(True)
    ejecutar(app)
    generar(app)
    assert app.session_state.datos_paciente[puntaje] != "No valorado"
    assert app.session_state.datos_paciente["Hallazgos estructurados"] != iniciales
    assert app.session_state.alertas_clinicas

    widget(app, "toggle", toggle).set_value(False)
    ejecutar(app)
    comprobar_invalidacion(app)
    assert widget(app, tipo, control).disabled
    assert aviso in [i.value for i in app.info]
    exportaciones.clear()
    generar(app)
    assert len(exportaciones) == 3
    for _, datos, _ in exportaciones:
        assert datos[puntaje] == "No valorado"
        assert datos[interpretacion] == "No valorado"
        assert datos["Hallazgos estructurados"] == iniciales
        assert resumen not in datos["Resumen clínico educativo"]
    assert app.session_state.alertas_clinicas == []

    widget(app, "toggle", toggle).set_value(True)
    ejecutar(app)
    comprobar_invalidacion(app)
    assert not widget(app, tipo, control).disabled
    widget(app, tipo, control).set_value(valor)
    ejecutar(app)
    generar(app)
    assert app.session_state.datos_paciente[puntaje] != "No valorado"
    assert resumen in app.session_state.datos_paciente["Resumen clínico educativo"]


def test_eva_obstetrica_desactivada_no_usa_valor_anterior():
    app = iniciar()
    widget(app, "selectbox", "Tipo de paciente").set_value("Obstétrico")
    ejecutar(app)
    widget(app, "checkbox", "Dolor abdominal intenso").set_value(True)
    widget(app, "toggle", "✅ Incluir EVA en la valoración").set_value(True)
    ejecutar(app)
    widget(app, "slider", "Intensidad del dolor").set_value(8)
    ejecutar(app)
    generar(app)
    widget(app, "toggle", "✅ Incluir EVA en la valoración").set_value(False)
    ejecutar(app)
    generar(app)
    assert app.session_state.datos_paciente["EVA dolor"] == "No valorado"
    assert app.session_state.datos_paciente["Interpretación EVA"] == "No valorado"
    assert not any(a["Área"] == "Dolor" for a in app.session_state.alertas_clinicas)
    assert any(a["Área"] == "Dolor / EVA" for a in app.session_state.alertas_clinicas)
    # El dolor registrado fuera de EVA sigue siendo un dato independiente.
    assert "dolor abdominal intenso" in app.session_state.datos_paciente["Hallazgos estructurados"]
