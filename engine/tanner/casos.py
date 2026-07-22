"""Carga y validación de casos educativos Tanner desde YAML."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from engine.tanner.modelos import CategoriaIndicio, IndicioTanner


@dataclass(frozen=True, slots=True)
class CasoTanner:
    """Caso educativo mínimo disponible para el motor Tanner."""

    id: str
    version: str
    estado: str
    titulo: str
    escena_inicial: str
    indicios_noticing: tuple[IndicioTanner, ...]
    uso_clinico_real: bool


def cargar_caso_tanner(ruta: str | Path) -> CasoTanner:
    """Carga un caso Tanner y valida su contrato mínimo."""

    ruta = Path(ruta)

    if not ruta.exists():
        raise FileNotFoundError(f"No existe el caso Tanner: {ruta}")

    try:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"YAML inválido en {ruta}: {error}") from error

    if not isinstance(datos, dict):
        raise ValueError("El caso Tanner debe contener un objeto YAML.")

    _validar_campos(
        datos,
        ("id", "version", "estado", "titulo", "proposito", "escena_inicial", "tanner"),
        contexto="caso",
    )

    proposito = datos["proposito"]
    escena = datos["escena_inicial"]
    tanner = datos["tanner"]

    if not isinstance(proposito, dict):
        raise ValueError("El campo 'proposito' debe ser un objeto.")

    if not isinstance(escena, dict):
        raise ValueError("El campo 'escena_inicial' debe ser un objeto.")

    if not isinstance(tanner, dict):
        raise ValueError("El campo 'tanner' debe ser un objeto.")

    _validar_campos(proposito, ("uso_clinico_real",), contexto="proposito")
    _validar_campos(escena, ("texto",), contexto="escena_inicial")
    _validar_campos(tanner, ("noticing",), contexto="tanner")

    noticing = tanner["noticing"]

    if not isinstance(noticing, dict):
        raise ValueError("El campo 'tanner.noticing' debe ser un objeto.")

    _validar_campos(noticing, ("indicios",), contexto="tanner.noticing")

    indicios_datos = noticing["indicios"]

    if not isinstance(indicios_datos, list) or not indicios_datos:
        raise ValueError(
            "El campo 'tanner.noticing.indicios' debe ser una lista no vacía."
        )

    indicios = tuple(
        _crear_indicio(indicio, posicion)
        for posicion, indicio in enumerate(indicios_datos, start=1)
    )

    ids = [indicio.id for indicio in indicios]
    if len(ids) != len(set(ids)):
        raise ValueError("Los identificadores de indicios deben ser únicos.")

    uso_clinico_real = proposito["uso_clinico_real"]
    if not isinstance(uso_clinico_real, bool):
        raise ValueError("'uso_clinico_real' debe ser booleano.")

    return CasoTanner(
        id=_texto_no_vacio(datos["id"], "id"),
        version=_texto_no_vacio(datos["version"], "version"),
        estado=_texto_no_vacio(datos["estado"], "estado"),
        titulo=_texto_no_vacio(datos["titulo"], "titulo"),
        escena_inicial=_texto_no_vacio(escena["texto"], "escena_inicial.texto"),
        indicios_noticing=indicios,
        uso_clinico_real=uso_clinico_real,
    )


def _crear_indicio(datos: Any, posicion: int) -> IndicioTanner:
    if not isinstance(datos, dict):
        raise ValueError(f"El indicio {posicion} debe ser un objeto.")

    _validar_campos(
        datos,
        ("id", "texto", "categoria", "esperado", "fundamento"),
        contexto=f"indicio {posicion}",
    )

    try:
        categoria = CategoriaIndicio(datos["categoria"])
    except ValueError as error:
        permitidas = ", ".join(categoria.value for categoria in CategoriaIndicio)
        raise ValueError(
            f"Categoría inválida en indicio {posicion}. Permitidas: {permitidas}"
        ) from error

    esperado = datos["esperado"]
    if not isinstance(esperado, bool):
        raise ValueError(
            f"El campo 'esperado' del indicio {posicion} debe ser booleano."
        )

    return IndicioTanner(
        id=_texto_no_vacio(datos["id"], f"indicio {posicion}.id"),
        texto=_texto_no_vacio(datos["texto"], f"indicio {posicion}.texto"),
        categoria=categoria,
        esperado=esperado,
        fundamento=_texto_no_vacio(
            datos["fundamento"],
            f"indicio {posicion}.fundamento",
        ),
    )


def _validar_campos(
    datos: dict[str, Any],
    campos: tuple[str, ...],
    *,
    contexto: str,
) -> None:
    faltantes = [campo for campo in campos if campo not in datos]

    if faltantes:
        raise ValueError(
            f"Faltan campos obligatorios en {contexto}: {', '.join(faltantes)}"
        )


def _texto_no_vacio(valor: Any, campo: str) -> str:
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"El campo '{campo}' debe contener texto.")
    return valor.strip()
