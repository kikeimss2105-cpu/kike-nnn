"""Configuración segura del comité agéntico de KIKE-NNN."""

from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
ARCHIVO_ENTORNO = RAIZ_PROYECTO / ".env.agents"


@dataclass(frozen=True)
class ConfiguracionAgentes:
    api_key: str
    base_url: str
    modelo_arquitecto: str
    modelo_programador: str
    modelo_programador_respaldo: str


def cargar_configuracion() -> ConfiguracionAgentes:
    """Carga y valida la configuración sin modificar el entorno global."""

    if not ARCHIVO_ENTORNO.is_file():
        raise RuntimeError(
            "No existe .env.agents en la raíz del proyecto."
        )

    valores = dotenv_values(ARCHIVO_ENTORNO)

    api_key = valores.get("NVIDIA_KIKENNN_KEY", "")
    base_url = valores.get("NVIDIA_BASE_URL", "")
    arquitecto = valores.get("MODEL_ARCHITECT", "")
    programador = valores.get("MODEL_PROGRAMMER", "")
    respaldo = valores.get("MODEL_TESTER", "")

    faltantes = [
        nombre
        for nombre, valor in {
            "NVIDIA_KIKENNN_KEY": api_key,
            "NVIDIA_BASE_URL": base_url,
            "MODEL_ARCHITECT": arquitecto,
            "MODEL_PROGRAMMER": programador,
            "MODEL_TESTER": respaldo,
        }.items()
        if not valor
    ]

    if faltantes:
        raise RuntimeError(
            "Configuración incompleta: " + ", ".join(faltantes)
        )

    if not api_key.startswith("nvapi-"):
        raise RuntimeError(
            "NVIDIA_KIKENNN_KEY no tiene formato válido."
        )

    return ConfiguracionAgentes(
        api_key=api_key,
        base_url=base_url,
        modelo_arquitecto=arquitecto,
        modelo_programador=programador,
        modelo_programador_respaldo=respaldo,
    )
