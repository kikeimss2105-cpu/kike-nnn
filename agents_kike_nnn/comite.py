"""Orquestación consultiva del comité KIKE-NNN."""

from dataclasses import dataclass
from datetime import datetime, timezone

from agents_kike_nnn.cliente_nvidia import (
    ClienteNvidia,
    ResultadoAgente,
)
from agents_kike_nnn.roles import (
    ROL_ARQUITECTO,
    ROL_AUDITOR,
    ROL_PROGRAMADOR,
)


@dataclass(frozen=True)
class ExpedienteComite:
    solicitud: str
    estado: str
    creado_en: str
    arquitectura: ResultadoAgente
    programacion: ResultadoAgente | None
    auditoria: ResultadoAgente | None

    @property
    def completo(self) -> bool:
        return (
            self.estado == "COMPLETO"
            and self.arquitectura.correcto
            and self.programacion is not None
            and self.programacion.correcto
            and self.auditoria is not None
            and self.auditoria.correcto
        )


class ComiteKikeNNN:
    """Coordina agentes sin concederles acceso de escritura."""

    def __init__(self, cliente: ClienteNvidia | None = None) -> None:
        self.cliente = cliente or ClienteNvidia()

    def evaluar(
        self,
        solicitud: str,
        contexto_controlado: str,
    ) -> ExpedienteComite:
        solicitud = solicitud.strip()
        contexto_controlado = contexto_controlado.strip()
        creado_en = datetime.now(timezone.utc).isoformat()

        if not solicitud:
            raise ValueError("La solicitud no puede estar vacía.")

        if not contexto_controlado:
            raise ValueError(
                "El comité requiere contexto controlado."
            )

        entrada_arquitecto = f"""
SOLICITUD:
{solicitud}

CONTEXTO CONTROLADO:
{contexto_controlado}

Analiza únicamente con este contexto.
Declara expresamente cualquier dato faltante.
""".strip()

        arquitectura = self.cliente.consultar_arquitecto(
            sistema=ROL_ARQUITECTO,
            solicitud=entrada_arquitecto,
        )

        if not arquitectura.correcto:
            return ExpedienteComite(
                solicitud=solicitud,
                estado="INCOMPLETO_FALLO_ARQUITECTO",
                creado_en=creado_en,
                arquitectura=arquitectura,
                programacion=None,
                auditoria=None,
            )

        entrada_programador = f"""
SOLICITUD ORIGINAL:
{solicitud}

CONTEXTO CONTROLADO:
{contexto_controlado}

INFORME DEL ARQUITECTO:
{arquitectura.contenido}

Entrega una propuesta mínima y un plan de pruebas.
No afirmes que modificaste archivos.
""".strip()

        programacion = self.cliente.consultar_programador(
            sistema=ROL_PROGRAMADOR,
            solicitud=entrada_programador,
            preferir_pro=False,
        )

        if not programacion.correcto:
            return ExpedienteComite(
                solicitud=solicitud,
                estado="INCOMPLETO_FALLO_PROGRAMADOR",
                creado_en=creado_en,
                arquitectura=arquitectura,
                programacion=programacion,
                auditoria=None,
            )

        entrada_auditor = f"""
SOLICITUD ORIGINAL:
{solicitud}

CONTEXTO CONTROLADO:
{contexto_controlado}

INFORME DEL ARQUITECTO:
{arquitectura.contenido}

PROPUESTA DEL PROGRAMADOR:
{programacion.contenido}

Busca riesgos, contradicciones, falsos positivos y ruptura de Tanner.
Emite exactamente uno de los veredictos permitidos.
""".strip()

        auditoria = self.cliente.consultar_arquitecto(
            sistema=ROL_AUDITOR,
            solicitud=entrada_auditor,
        )

        estado = (
            "COMPLETO"
            if auditoria.correcto
            else "INCOMPLETO_FALLO_AUDITOR"
        )

        return ExpedienteComite(
            solicitud=solicitud,
            estado=estado,
            creado_en=creado_en,
            arquitectura=arquitectura,
            programacion=programacion,
            auditoria=auditoria,
        )
