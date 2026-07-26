from agents_kike_nnn.cliente_nvidia import ResultadoAgente
from agents_kike_nnn.comite import ComiteKikeNNN, ExpedienteComite


def resultado(correcto: bool, contenido: str = "") -> ResultadoAgente:
    return ResultadoAgente(
        correcto=correcto,
        modelo_solicitado="modelo-prueba",
        modelo_utilizado="modelo-prueba",
        contenido=contenido,
        duracion_segundos=0.1,
        uso_respaldo=False,
        tipo_error=None if correcto else "ErrorSimulado",
        detalle_error=None if correcto else "Fallo simulado",
    )


class ClienteSimulado:
    def __init__(
        self,
        arquitecto: ResultadoAgente,
        programador: ResultadoAgente,
        auditor: ResultadoAgente,
    ) -> None:
        self.arquitecto = arquitecto
        self.programador = programador
        self.auditor = auditor
        self.llamadas_arquitecto = 0
        self.llamadas_programador = 0

    def consultar_arquitecto(self, **kwargs) -> ResultadoAgente:
        self.llamadas_arquitecto += 1
        if self.llamadas_arquitecto == 1:
            return self.arquitecto
        return self.auditor

    def consultar_programador(self, **kwargs) -> ResultadoAgente:
        self.llamadas_programador += 1
        return self.programador


def test_comite_completa_los_tres_roles():
    cliente = ClienteSimulado(
        arquitecto=resultado(True, "arquitectura"),
        programador=resultado(True, "programacion"),
        auditor=resultado(True, "APROBABLE_PARA_IMPLEMENTACION"),
    )

    comite = ComiteKikeNNN(cliente=cliente)
    expediente = comite.evaluar(
        solicitud="Mejorar retroalimentación Noticing.",
        contexto_controlado="Caso YAML y pruebas existentes.",
    )

    assert expediente.estado == "COMPLETO"
    assert expediente.completo is True
    assert expediente.arquitectura.contenido == "arquitectura"
    assert expediente.programacion is not None
    assert expediente.auditoria is not None
    assert cliente.llamadas_arquitecto == 2
    assert cliente.llamadas_programador == 1


def test_comite_se_detiene_si_falla_arquitecto():
    cliente = ClienteSimulado(
        arquitecto=resultado(False),
        programador=resultado(True, "no debe usarse"),
        auditor=resultado(True, "no debe usarse"),
    )

    expediente = ComiteKikeNNN(cliente=cliente).evaluar(
        solicitud="Cambio de prueba.",
        contexto_controlado="Contexto controlado.",
    )

    assert expediente.estado == "INCOMPLETO_FALLO_ARQUITECTO"
    assert expediente.completo is False
    assert expediente.programacion is None
    assert expediente.auditoria is None
    assert cliente.llamadas_programador == 0
    assert cliente.llamadas_arquitecto == 1


def test_comite_se_detiene_si_falla_programador():
    cliente = ClienteSimulado(
        arquitecto=resultado(True, "arquitectura"),
        programador=resultado(False),
        auditor=resultado(True, "no debe usarse"),
    )

    expediente = ComiteKikeNNN(cliente=cliente).evaluar(
        solicitud="Cambio de prueba.",
        contexto_controlado="Contexto controlado.",
    )

    assert expediente.estado == "INCOMPLETO_FALLO_PROGRAMADOR"
    assert expediente.completo is False
    assert expediente.programacion is not None
    assert expediente.auditoria is None
    assert cliente.llamadas_programador == 1
    assert cliente.llamadas_arquitecto == 1


def test_reanudar_no_repite_informe_del_arquitecto():
    arquitectura_previa = resultado(
        True,
        "arquitectura ya aprobada",
    )
    expediente_previo = ExpedienteComite(
        solicitud="Revisar Noticing.",
        estado="INCOMPLETO_FALLO_PROGRAMADOR",
        creado_en="2026-07-26T00:00:00+00:00",
        arquitectura=arquitectura_previa,
        programacion=resultado(False),
        auditoria=None,
    )

    cliente = ClienteSimulado(
        arquitecto=resultado(
            True,
            "no debe volver a solicitarse",
        ),
        programador=resultado(
            True,
            "propuesta recuperada",
        ),
        auditor=resultado(
            True,
            "APROBABLE_PARA_IMPLEMENTACION",
        ),
    )

    # La siguiente llamada a Nemotron debe ser auditoría,
    # no una nueva arquitectura.
    cliente.llamadas_arquitecto = 1

    reanudado = ComiteKikeNNN(cliente=cliente).reanudar(
        expediente=expediente_previo,
        contexto_controlado="Contexto autorizado.",
    )

    assert reanudado.estado == "COMPLETO"
    assert reanudado.completo is True
    assert reanudado.arquitectura is arquitectura_previa
    assert reanudado.programacion is not None
    assert reanudado.programacion.contenido == ("propuesta recuperada")
    assert reanudado.auditoria is not None
    assert reanudado.auditoria.contenido == ("APROBABLE_PARA_IMPLEMENTACION")
    assert cliente.llamadas_programador == 1
    assert cliente.llamadas_arquitecto == 2
