"""Persistencia local de expedientes del comité."""

import json
from dataclasses import asdict
from pathlib import Path

from agents_kike_nnn.cliente_nvidia import ResultadoAgente
from agents_kike_nnn.comite import ExpedienteComite
from agents_kike_nnn.contexto import RAIZ_PROYECTO


DIRECTORIO_EXPEDIENTES = RAIZ_PROYECTO / ".agent_runs"


def guardar_expediente(
    expediente: ExpedienteComite,
    *,
    directorio: Path = DIRECTORIO_EXPEDIENTES,
) -> Path:
    """Guarda un expediente sin incluir claves ni configuración."""

    directorio.mkdir(parents=True, exist_ok=True)

    marca = expediente.creado_en.replace(":", "-").replace("+", "_")
    destino = directorio / f"comite_{marca}.json"

    datos = asdict(expediente)
    datos["esquema"] = 1

    destino.write_text(
        json.dumps(
            datos,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    destino.chmod(0o600)

    return destino


def _cargar_resultado(
    datos: dict | None,
) -> ResultadoAgente | None:
    if datos is None:
        return None

    return ResultadoAgente(**datos)


def cargar_expediente(ruta: Path) -> ExpedienteComite:
    """Reconstruye un expediente previamente guardado."""

    datos = json.loads(ruta.read_text(encoding="utf-8"))

    if datos.get("esquema") != 1:
        raise ValueError("Versión de expediente no compatible.")

    return ExpedienteComite(
        solicitud=datos["solicitud"],
        estado=datos["estado"],
        creado_en=datos["creado_en"],
        arquitectura=_cargar_resultado(
            datos["arquitectura"]
        ),
        programacion=_cargar_resultado(
            datos.get("programacion")
        ),
        auditoria=_cargar_resultado(
            datos.get("auditoria")
        ),
    )
