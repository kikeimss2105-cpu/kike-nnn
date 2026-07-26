from unittest.mock import patch

import httpx
from openai import APITimeoutError, InternalServerError

from agents_kike_nnn.cliente_nvidia import ClienteNvidia


def test_programador_usa_flash_por_defecto():
    cliente = ClienteNvidia()

    with patch.object(
        cliente,
        "_consultar",
        return_value=("respuesta flash", 1.5),
    ) as consultar:
        resultado = cliente.consultar_programador(
            sistema="sistema",
            solicitud="solicitud",
        )

    assert resultado.correcto is True
    assert resultado.modelo_utilizado == (
        cliente.configuracion.modelo_programador_respaldo
    )
    assert resultado.uso_respaldo is False
    assert resultado.contenido == "respuesta flash"

    consultar.assert_called_once()
    assert consultar.call_args.kwargs["modelo"] == (
        cliente.configuracion.modelo_programador_respaldo
    )


def test_programador_pro_degrada_a_flash_si_expira():
    cliente = ClienteNvidia()
    error_timeout = APITimeoutError(
        request=httpx.Request("POST", "https://example.invalid")
    )

    with patch.object(
        cliente,
        "_consultar",
        side_effect=[
            error_timeout,
            ("respuesta de respaldo", 2.0),
        ],
    ) as consultar:
        resultado = cliente.consultar_programador(
            sistema="sistema",
            solicitud="solicitud",
            preferir_pro=True,
        )

    assert resultado.correcto is True
    assert resultado.modelo_solicitado == (
        cliente.configuracion.modelo_programador
    )
    assert resultado.modelo_utilizado == (
        cliente.configuracion.modelo_programador_respaldo
    )
    assert resultado.uso_respaldo is True
    assert resultado.tipo_error == "APITimeoutError"
    assert resultado.contenido == "respuesta de respaldo"
    assert consultar.call_count == 2


def test_arquitecto_usa_nemotron_ultra():
    cliente = ClienteNvidia()

    with patch.object(
        cliente,
        "_consultar",
        return_value=("respuesta del arquitecto", 3.0),
    ) as consultar:
        resultado = cliente.consultar_arquitecto(
            sistema="sistema",
            solicitud="solicitud",
        )

    assert resultado.correcto is True
    assert resultado.modelo_utilizado == (
        cliente.configuracion.modelo_arquitecto
    )
    assert resultado.uso_respaldo is False
    assert resultado.contenido == "respuesta del arquitecto"

    consultar.assert_called_once()


def test_flash_reintenta_una_vez_ante_error_503():
    cliente = ClienteNvidia()

    respuesta_503 = httpx.Response(
        status_code=503,
        request=httpx.Request(
            "POST",
            "https://example.invalid",
        ),
    )
    error_503 = InternalServerError(
        "Servidor saturado",
        response=respuesta_503,
        body={
            "error": {
                "message": "ResourceExhausted",
            }
        },
    )

    with (
        patch(
            "agents_kike_nnn.cliente_nvidia.sleep"
        ) as esperar,
        patch.object(
            cliente,
            "_consultar",
            side_effect=[
                error_503,
                ("respuesta recuperada", 1.0),
            ],
        ) as consultar,
    ):
        resultado = cliente.consultar_programador(
            sistema="sistema",
            solicitud="solicitud",
            preferir_pro=False,
        )

    assert resultado.correcto is True
    assert resultado.contenido == "respuesta recuperada"
    assert resultado.modelo_utilizado == (
        cliente.configuracion.modelo_programador_respaldo
    )
    assert resultado.uso_respaldo is False
    assert resultado.tipo_error == "InternalServerError"
    assert consultar.call_count == 2
    esperar.assert_called_once_with(5)
