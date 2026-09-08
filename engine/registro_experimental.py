"""Registro experimental v1: proyección del estado vigente, sin persistencia.

Los textos corresponden exclusivamente a casos educativos sin datos personales.
COMPLETADO describe cierre de captura; no evalúa corrección clínica.
"""
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
import math
from numbers import Integral, Real
import re
from uuid import UUID, uuid4

VERSION_APP = "1.0.0-rc1"
CAMPOS = {
    "participante_id", "sesion_id", "momento", "caso_id", "intento_id",
    "version_app", "timestamp", "perfil", "valoracion", "sugerencias",
    "decisiones", "criterios", "argumentos", "estado", "schema_version",
    "estado_tecnico", "metadatos_resultados",
}


def utc_ahora():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


@dataclass(frozen=True)
class SesionExperimental:
    participante_id: str
    sesion_id: str
    momento: str
    caso_id: str | None

    def __post_init__(self):
        if not re.fullmatch(r"P[0-9]{3,8}", self.participante_id):
            raise ValueError("Usa un código seudónimo P seguido de 3 a 8 dígitos, por ejemplo P001.")
        if self.momento not in {"PRE", "POST"}:
            raise ValueError("Selecciona PRE o POST.")
        UUID(self.sesion_id)
        if self.caso_id is not None and not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,63}", self.caso_id):
            raise ValueError("El caso debe ser un código de protocolo en mayúsculas, sin datos personales.")


def nueva_sesion(participante_id, momento, caso_id=None):
    return SesionExperimental(participante_id, uuid4().hex, momento, caso_id or None)


def normalizar(valor):
    """Representación JSON explícita de dataclasses, enums y números del motor."""
    if is_dataclass(valor):
        return normalizar(asdict(valor))
    if isinstance(valor, Enum):
        return normalizar(valor.value)
    if valor is None or isinstance(valor, (str, bool)):
        return valor
    if isinstance(valor, Integral):
        return int(valor)
    if isinstance(valor, Real):
        return float(valor) if math.isfinite(valor) else None
    if isinstance(valor, dict):
        return {k: normalizar(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [normalizar(v) for v in valor]
    raise ValueError(f"Tipo no serializable en registro: {type(valor).__name__}")


def construir_registro(sesion, estado, valoracion_actual):
    """Rechaza estado obsoleto o ajeno; nunca combina resultados y entradas nuevas."""
    sesion.__post_init__()
    if estado.get("resultados_invalidados"):
        raise ValueError("La valoración cambió; regenera antes de exportar.")
    generado = estado.get("plan_generado", False)
    fallo = estado.get("experimental_fallo", False)
    intento = estado.get("intento_id") if generado else None
    if generado or fallo:
        if estado.get("experimental_vinculo") != (sesion.sesion_id, intento):
            raise ValueError("El intento no pertenece a esta sesión experimental.")
        if estado.get("valoracion_generada") != valoracion_actual:
            raise ValueError("La valoración no corresponde al intento.")
    sugerencias = estado["df_resultados"].to_dict("records") if generado else []
    respuestas = estado.get("justificaciones", {}) if generado else {}
    nombres = {fila["NANDA"] for fila in sugerencias}
    if set(respuestas) - nombres:
        raise ValueError("Hay respuestas ajenas a las sugerencias del intento.")
    decisiones = {n: respuestas.get(n, {}).get("decision", "Sin decidir") for n in sorted(nombres)}
    criterios = {n: respuestas.get(n, {}).get("criterios", []) for n in sorted(nombres)}
    argumentos = {n: respuestas.get(n, {}).get("justificacion", "") for n in sorted(nombres)}
    tecnico = "GENERACION_FALLIDA" if fallo else (
        estado["df_resultados"].attrs.get("estado_parsing", "PARSING_CONFIABLE")
        if generado else "NO_GENERADO"
    )
    completo = generado and all(
        decisiones[n] in {"Aceptado", "Rechazado"} and argumentos[n].strip()
        for n in nombres
    )
    registro = {
        **asdict(sesion), "schema_version": 1, "intento_id": intento,
        "version_app": VERSION_APP, "timestamp": utc_ahora(),
        "perfil": valoracion_actual["perfil"][0],
        "valoracion": valoracion_actual, "sugerencias": sugerencias,
        "decisiones": decisiones, "criterios": criterios, "argumentos": argumentos,
        "estado": "FALLO" if fallo or tecnico == "PARSING_NO_CONFIABLE" else (
            "COMPLETADO" if completo else "INCOMPLETO"
        ),
        "estado_tecnico": tecnico,
        "metadatos_resultados": estado["df_resultados"].attrs if generado else {},
    }
    return normalizar(registro)


def serializar_registro(registro):
    recuperar_registro(json.dumps(registro, ensure_ascii=False, allow_nan=False))
    return json.dumps(registro, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2).encode("utf-8")


def recuperar_registro(contenido):
    registro = json.loads(contenido)
    if set(registro) != CAMPOS or registro["schema_version"] != 1:
        raise ValueError("Contrato de registro no reconocido.")
    SesionExperimental(**{k: registro[k] for k in ("participante_id", "sesion_id", "momento", "caso_id")})
    if registro["estado"] not in {"COMPLETADO", "INCOMPLETO", "FALLO"}:
        raise ValueError("Estado inválido.")
    if registro["intento_id"] is not None:
        UUID(registro["intento_id"])
    if not isinstance(registro["sugerencias"], list) or not all(
        isinstance(f, dict) and isinstance(f.get("NANDA"), str) for f in registro["sugerencias"]
    ):
        raise ValueError("Sugerencias inválidas.")
    for campo in ("valoracion", "decisiones", "criterios", "argumentos", "metadatos_resultados"):
        if not isinstance(registro[campo], dict):
            raise ValueError(f"Campo inválido: {campo}")
    nombres = {f["NANDA"] for f in registro["sugerencias"]}
    if any(set(registro[c]) != nombres for c in ("decisiones", "criterios", "argumentos")):
        raise ValueError("Respuestas sin vínculo con sugerencias.")
    if any(d not in {"Aceptado", "Rechazado", "Sin decidir"} for d in registro["decisiones"].values()):
        raise ValueError("Decisión inválida.")
    if any(not isinstance(a, str) for a in registro["argumentos"].values()):
        raise ValueError("Argumento inválido.")
    if any(not isinstance(c, list) or any(not isinstance(v, str) for v in c) for c in registro["criterios"].values()):
        raise ValueError("Criterios inválidos.")
    if registro["estado"] == "COMPLETADO" and (
        registro["intento_id"] is None
        or registro["estado_tecnico"] != "PARSING_CONFIABLE"
        or any(d == "Sin decidir" for d in registro["decisiones"].values())
        or any(not a.strip() for a in registro["argumentos"].values())
    ):
        raise ValueError("Registro sin cierre completo.")
    if registro["perfil"] != registro["valoracion"].get("perfil", [None])[0]:
        raise ValueError("Perfil ajeno a la valoración.")
    if not isinstance(registro["version_app"], str) or not registro["version_app"]:
        raise ValueError("Versión ausente.")
    if datetime.fromisoformat(registro["timestamp"]).utcoffset() is None:
        raise ValueError("El timestamp requiere zona horaria.")
    return registro


def nombre_archivo(registro):
    contenido = serializar_registro(registro)
    return (
        f"kike_{registro['participante_id']}_{registro['momento']}_"
        f"{registro['sesion_id']}_{registro['intento_id'] or 'sin-intento'}_"
        f"{sha256(contenido).hexdigest()}.json"
    )
