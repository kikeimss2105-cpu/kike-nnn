from agents_kike_nnn.cliente_nvidia import ResultadoAgente
from agents_kike_nnn.comite import ExpedienteComite
from agents_kike_nnn.expedientes import (
    cargar_expediente,
    guardar_expediente,
)


def crear_resultado(
    correcto: bool,
    contenido: str = "",
) -> ResultadoAgente:
    return ResultadoAgente(
        correcto=correcto,
        modelo_solicitado="modelo-prueba",
        modelo_utilizado="modelo-prueba",
        contenido=contenido,
        duracion_segundos=1.0,
        uso_respaldo=False,
        tipo_error=None if correcto else "ErrorSimulado",
        detalle_error=None if correcto else "Fallo simulado",
    )


def test_guarda_y_recupera_expediente_incompleto(tmp_path):
    expediente = ExpedienteComite(
        solicitud="Revisar Noticing.",
        estado="INCOMPLETO_FALLO_PROGRAMADOR",
        creado_en="2026-07-26T00:00:00+00:00",
        arquitectura=crear_resultado(
            True,
            "Informe del arquitecto.",
        ),
        programacion=crear_resultado(False),
        auditoria=None,
    )

    ruta = guardar_expediente(
        expediente,
        directorio=tmp_path,
    )
    recuperado = cargar_expediente(ruta)

    assert ruta.is_file()
    assert oct(ruta.stat().st_mode & 0o777) == "0o600"
    assert recuperado == expediente
    assert recuperado.arquitectura.contenido == (
        "Informe del arquitecto."
    )
    assert recuperado.auditoria is None


def test_expediente_no_contiene_clave_api(tmp_path):
    expediente = ExpedienteComite(
        solicitud="Solicitud segura.",
        estado="COMPLETO",
        creado_en="2026-07-26T00:00:00+00:00",
        arquitectura=crear_resultado(True, "arquitectura"),
        programacion=crear_resultado(True, "programacion"),
        auditoria=crear_resultado(True, "auditoria"),
    )

    ruta = guardar_expediente(
        expediente,
        directorio=tmp_path,
    )
    contenido = ruta.read_text(encoding="utf-8")

    assert "nvapi-" not in contenido
    assert "NVIDIA_KIKENNN_KEY" not in contenido
