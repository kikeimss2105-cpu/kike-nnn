"""Contrato experimental A–J y estados técnicos, sin inferencias clínicas."""
from copy import deepcopy
from datetime import datetime
import json
from uuid import uuid4

import pandas as pd
import pytest

from engine.registro_experimental import (
    CAMPOS, construir_registro, nueva_sesion, nombre_archivo,
    recuperar_registro, serializar_registro,
)


def captura(sesion, filas=None, respuestas=None):
    valoracion = {"perfil": ("Adulto", 0, "No especificado"), "texto": ("", "", "", ""), "hallazgos": {"Disnea": False}}
    intento = uuid4().hex
    estado = {
        "plan_generado": True, "valoracion_generada": deepcopy(valoracion),
        "intento_id": intento, "experimental_vinculo": (sesion.sesion_id, intento),
        "df_resultados": pd.DataFrame(filas or []), "justificaciones": respuestas or {},
    }
    return estado, valoracion


def registro(sesion):
    return construir_registro(sesion, *captura(sesion))


def test_a_pre_post_vinculados_y_b_participantes_separados():
    pre, post, otro = [registro(nueva_sesion(p, m)) for p, m in [("P001", "PRE"), ("P001", "POST"), ("P002", "PRE")]]
    assert pre["participante_id"] == post["participante_id"] != otro["participante_id"]
    assert [pre["momento"], post["momento"]] == ["PRE", "POST"]
    assert len({r["sesion_id"] for r in (pre, post, otro)}) == 3


def test_c_sesiones_distintas_mismo_participante():
    assert nueva_sesion("P001", "PRE").sesion_id != nueva_sesion("P001", "PRE").sesion_id


def test_d_intentos_no_mezclan_respuestas_ni_snapshot():
    sesion = nueva_sesion("P001", "PRE")
    estado, valoracion = captura(sesion, [{"NANDA": "Ejemplo", "Código": "TEST"}], {
        "Ejemplo": {"decision": "Rechazado", "criterios": ["Criterio del caso"], "justificacion": "Argumento uno"},
    })
    primero = construir_registro(sesion, estado, valoracion)
    segundo = registro(sesion)
    assert primero["intento_id"] != segundo["intento_id"]
    assert segundo["argumentos"] == {}
    estado["justificaciones"]["Ejemplo"]["justificacion"] = "Editado"
    assert primero["argumentos"]["Ejemplo"] == "Argumento uno"
    estado["intento_id"] = uuid4().hex
    with pytest.raises(ValueError, match="no pertenece"):
        construir_registro(sesion, estado, valoracion)


def test_e_cero_sugerencias_completado_exportable():
    r = registro(nueva_sesion("P001", "PRE"))
    assert r["sugerencias"] == []
    assert r["decisiones"] == r["criterios"] == r["argumentos"] == {}
    assert r["estado"] == "COMPLETADO"
    assert recuperar_registro(serializar_registro(r)) == r


@pytest.mark.parametrize("codigo", ["", " ", "P1", "p001", "P000000000", "P001 POST", "../P001", "alguien@example.org", "Ana"])
def test_f_codigo_invalido_rechazado(codigo):
    with pytest.raises(ValueError):
        nueva_sesion(codigo, "PRE")


@pytest.mark.parametrize("momento", ["", "pre", "POST ", "OTRO", "Seleccionar"])
def test_g_momento_invalido_rechazado(momento):
    with pytest.raises(ValueError):
        nueva_sesion("P001", momento)


def test_h_esquema_sin_campos_personales_y_sin_volcado_session_state():
    sesion = nueva_sesion("P001", "PRE")
    estado, valoracion = captura(sesion)
    prohibidos = {"nombre", "matricula", "matrícula", "correo", "telefono", "teléfono", "direccion", "dirección", "fecha_nacimiento"}
    estado.update({k: "NO EXPORTAR" for k in prohibidos})
    r = construir_registro(sesion, estado, valoracion)
    assert set(r) == CAMPOS
    assert not prohibidos.intersection(r)
    assert "NO EXPORTAR" not in serializar_registro(r).decode()
    r["correo"] = "no"
    with pytest.raises(ValueError):
        recuperar_registro(json.dumps(r))


def test_i_rechaza_valoracion_obsoleta_y_sesion_ajena():
    sesion = nueva_sesion("P001", "PRE")
    estado, valoracion = captura(sesion)
    with pytest.raises(ValueError):
        construir_registro(nueva_sesion("P002", "POST"), estado, valoracion)
    valoracion["hallazgos"]["Disnea"] = True
    with pytest.raises(ValueError, match="valoración"):
        construir_registro(sesion, estado, valoracion)
    estado["resultados_invalidados"] = True
    with pytest.raises(ValueError):
        construir_registro(sesion, estado, valoracion)


def test_j_roundtrip_y_nombre_no_ambiguo(tmp_path):
    r = registro(nueva_sesion("P001", "PRE", "CASO-001"))
    archivo = tmp_path / nombre_archivo(r)
    archivo.write_bytes(serializar_registro(r))
    assert recuperar_registro(archivo.read_bytes()) == r
    assert r["version_app"] == "1.0.0-rc1"
    assert datetime.fromisoformat(r["timestamp"]).utcoffset().total_seconds() == 0
    assert nombre_archivo(r) == nombre_archivo(deepcopy(r))
    assert nombre_archivo(r) != nombre_archivo(registro(nueva_sesion("P001", "PRE")))


def test_incompleto_sin_generacion_y_sin_argumento():
    sesion = nueva_sesion("P001", "PRE")
    estado, valoracion = captura(sesion, [{"NANDA": "Ejemplo"}], {"Ejemplo": {"decision": "Aceptado", "justificacion": " "}})
    assert construir_registro(sesion, estado, valoracion)["estado"] == "INCOMPLETO"
    r = construir_registro(sesion, {}, valoracion)
    assert r["estado"] == "INCOMPLETO"
    assert r["intento_id"] is None and r["sugerencias"] == []


def test_parsing_no_confiable_es_fallo_incluso_sin_sugerencias():
    sesion = nueva_sesion("P001", "PRE")
    estado, valoracion = captura(sesion)
    estado["df_resultados"].attrs["estado_parsing"] = "PARSING_NO_CONFIABLE"
    assert construir_registro(sesion, estado, valoracion)["estado"] == "FALLO"


def test_respuestas_ajenas_rechazadas():
    sesion = nueva_sesion("P001", "PRE")
    estado, valoracion = captura(sesion, respuestas={"Ajeno": {}})
    with pytest.raises(ValueError, match="ajenas"):
        construir_registro(sesion, estado, valoracion)


def test_metadatos_y_dataclasses_del_motor_recuperables():
    from engine.glasgow import evaluar_glasgow
    sesion = nueva_sesion("P001", "PRE")
    estado, valoracion = captura(sesion)
    valoracion["glasgow"] = evaluar_glasgow(4, 5, 6, valorado=False)
    estado["valoracion_generada"] = deepcopy(valoracion)
    estado["df_resultados"].attrs["evidencias"] = []
    r = construir_registro(sesion, estado, valoracion)
    assert r["valoracion"]["glasgow"]["valorado"] is False
    assert r["metadatos_resultados"]["evidencias"] == []
    assert recuperar_registro(serializar_registro(r)) == r


@pytest.mark.parametrize("campo,valor", [("estado", "OTRO"), ("sugerencias", {}), ("argumentos", []), ("intento_id", "no-uuid"), ("version_app", "")])
def test_recuperacion_rechaza_contrato_corrupto(campo, valor):
    r = registro(nueva_sesion("P001", "PRE"))
    r[campo] = valor
    with pytest.raises(ValueError):
        recuperar_registro(json.dumps(r))
