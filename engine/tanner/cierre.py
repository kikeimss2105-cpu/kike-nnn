"""Controles de habilitación para casos Tanner incompletos.

Este módulo no evalúa contenido clínico. Expone de forma determinista si el
contrato YAML permite habilitar fases posteriores o si requiere revisión
humana antes de conectarlas a una interfaz.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


BLOQUEO_CLINICO = "BLOQUEO_CLINICO"


@dataclass(frozen=True, slots=True)
class EstadoCierreTanner:
    caso_id: str
    noticing_definido: bool
    interpreting_definido: bool
    responding_habilitado: bool
    reflecting_habilitado: bool
    farmacologia_habilitada: bool
    maquina_estados_habilitada: bool
    bloqueos: tuple[str, ...]

    @property
    def ciclo_completo_habilitado(self) -> bool:
        return (
            self.noticing_definido
            and self.interpreting_definido
            and self.responding_habilitado
            and self.reflecting_habilitado
            and self.farmacologia_habilitada
            and self.maquina_estados_habilitada
            and not self.bloqueos
        )


def inspeccionar_cierre_tanner(ruta: str | Path) -> EstadoCierreTanner:
    """Lee estados explícitos del YAML; no completa contratos por analogía."""

    ruta = Path(ruta)
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict) or not isinstance(datos.get("tanner"), dict):
        raise ValueError("El caso no contiene un contrato Tanner válido.")

    tanner: dict[str, Any] = datos["tanner"]
    noticing_definido = _seccion_no_vacia(tanner.get("noticing"))
    interpreting_definido = _seccion_no_vacia(tanner.get("interpreting"))

    responding = tanner.get("responding")
    responding_habilitado = (
        isinstance(responding, dict)
        and responding.get("estado") in {
            "validado_clinicamente",
            "validado_clinicamente_no_farmacologico",
            "validado_clinica_y_pedagogicamente",
        }
    )

    acciones_farmacologicas = responding.get("acciones_farmacologicas", {}) if isinstance(responding, dict) else {}
    farmacologia_habilitada = (
        isinstance(acciones_farmacologicas, dict)
        and acciones_farmacologicas.get("estado") == "validada_clinicamente"
    )

    reflecting = tanner.get("reflecting")
    reflecting_habilitado = (
        isinstance(reflecting, dict)
        and reflecting.get("estado") in {"validado_pedagogicamente", "validado_clinica_y_pedagogicamente"}
    )

    maquina_estados = datos.get("maquina_de_estados")
    maquina_estados_habilitada = (
        isinstance(maquina_estados, dict)
        and maquina_estados.get("estado") == "validada_clinicamente"
    )

    bloqueos: list[str] = []
    if not responding_habilitado:
        bloqueos.append(
            f"{BLOQUEO_CLINICO}: Responding requiere contrato y validación humana explícita."
        )
    if not reflecting_habilitado:
        bloqueos.append(
            f"{BLOQUEO_CLINICO}: Reflecting requiere clave y validación pedagógica explícita."
        )
    if not farmacologia_habilitada:
        bloqueos.append(
            f"{BLOQUEO_CLINICO}: Farmacología permanece bloqueada hasta validación clínica explícita."
        )
    if not maquina_estados_habilitada:
        bloqueos.append(
            f"{BLOQUEO_CLINICO}: La máquina de estados permanece bloqueada hasta validación clínica explícita."
        )

    return EstadoCierreTanner(
        caso_id=str(datos.get("id", "")),
        noticing_definido=noticing_definido,
        interpreting_definido=interpreting_definido,
        responding_habilitado=responding_habilitado,
        reflecting_habilitado=reflecting_habilitado,
        farmacologia_habilitada=farmacologia_habilitada,
        maquina_estados_habilitada=maquina_estados_habilitada,
        bloqueos=tuple(bloqueos),
    )


def _seccion_no_vacia(valor: Any) -> bool:
    return isinstance(valor, dict) and bool(valor)
