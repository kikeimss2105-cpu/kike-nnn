"""Contratos de datos para las escalas neonatales deterministas."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ResultadoEscalaNeonatal:
    """Resultado explicable; ``total=None`` significa que no se calculó."""

    escala: str
    total: int | None
    desglose: Mapping[str, int | None]
    datos_faltantes: tuple[str, ...]
    interpretacion: str | None = None
    formula: str | None = None
    edad_gestacional_semanas: float | None = None
    semanas_completas: int | None = None
    dias_adicionales: int | None = None

    def __post_init__(self) -> None:
        # Evita que el desglose pueda cambiar después de producir el resultado.
        object.__setattr__(self, "desglose", MappingProxyType(dict(self.desglose)))

    @property
    def completo(self) -> bool:
        return not self.datos_faltantes

    @property
    def calculado(self) -> bool:
        return self.total is not None

    @property
    def componentes(self) -> Mapping[str, int | None]:
        """Alias semántico útil para Capurro y serialización educativa."""

        return self.desglose


def validar_componentes(
    componentes: Mapping[str, int | None],
    valores_permitidos: Mapping[str, frozenset[int]],
) -> tuple[str, ...]:
    """Valida valores presentes y devuelve, en orden, los no valorados."""

    faltantes: list[str] = []
    for nombre, valor in componentes.items():
        if valor is None:
            faltantes.append(nombre)
            continue
        if isinstance(valor, bool) or not isinstance(valor, int):
            raise ValueError(f"'{nombre}' debe ser un entero o None (no valorado).")
        permitidos = valores_permitidos[nombre]
        if valor not in permitidos:
            opciones = ", ".join(str(item) for item in sorted(permitidos))
            raise ValueError(f"Valor inválido para '{nombre}': {valor}. Permitidos: {opciones}.")
    return tuple(faltantes)
