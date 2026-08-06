"""Cliente real (NVIDIA, vía SDK de OpenAI) para evaluar la fase Interpreting.

Deliberadamente independiente de agents_kike_nnn/ (el sistema de comité):
este módulo tiene un único propósito — identificar presencia de conceptos
y relaciones ya definidos en un caso Tanner — y no depende de esa
infraestructura más amplia.

Requiere un archivo .env.tanner en la raíz del proyecto con:
    NVIDIA_TANNER_KEY=nvapi-...
    NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
    NVIDIA_TANNER_MODEL=deepseek-ai/deepseek-v3   (o el modelo que prefieras)

Este archivo NUNCA debe subirse a git — confirma que .env.tanner está en
.gitignore antes de crearlo.

Reintentos: probar_interpreting.py (2026-08-02) mostró una tasa de falla
transitoria real de 2 de 3 llamadas (529 Overloaded, luego timeout) —
no es hipotético. Por eso este cliente reintenta hasta 3 veces con
espera corta antes de reportar el fallo al estudiante. El SDK de OpenAI
se deja en max_retries=0 a propósito: el reintento se controla aquí,
explícitamente, para poder registrar cada intento.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values
from openai import OpenAI

from engine.tanner.interpreting import RespuestaClienteLLM

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent.parent
ARCHIVO_ENTORNO = RAIZ_PROYECTO / ".env.tanner"

_INTENTOS_MAXIMOS = 3
_ESPERA_ENTRE_INTENTOS_SEGUNDOS = 1.5

_PROMPT_SISTEMA = """Eres un asistente que identifica, en el texto de un \
estudiante de enfermería, qué conceptos clínicos y qué relaciones entre \
ellos están presentes — SIN exigir frase literal ni vocabulario exacto. \
Basta con que la idea esté presente, aunque esté redactada distinto.

Reglas estrictas:
1. Solo puedes marcar como detectado un concepto o relación que aparezca \
LITERALMENTE en las listas que se te dan. Nunca inventes ni agregues \
conceptos o relaciones fuera de esas listas.
2. Responde ÚNICAMENTE con un objeto JSON, sin texto antes ni después, \
con esta forma exacta:
{"conceptos_detectados": ["id1", "id2"], "relaciones_detectadas": ["id3"]}
3. Si no detectas ninguno, responde con listas vacías. No es un error \
que las listas salgan vacías — es preferible eso a inventar detecciones.
"""


@dataclass(frozen=True)
class ConfiguracionTanner:
    api_key: str
    base_url: str
    modelo: str


def cargar_configuracion_tanner() -> ConfiguracionTanner:
    if not ARCHIVO_ENTORNO.is_file():
        raise RuntimeError(
            f"No existe {ARCHIVO_ENTORNO.name} en la raíz del proyecto. "
            "Crea el archivo con NVIDIA_TANNER_KEY, NVIDIA_BASE_URL y "
            "NVIDIA_TANNER_MODEL antes de usar el cliente real."
        )

    valores = dotenv_values(ARCHIVO_ENTORNO)
    api_key = valores.get("NVIDIA_TANNER_KEY", "")
    base_url = valores.get("NVIDIA_BASE_URL", "")
    modelo = valores.get("NVIDIA_TANNER_MODEL", "")

    faltantes = [
        nombre
        for nombre, valor in {
            "NVIDIA_TANNER_KEY": api_key,
            "NVIDIA_BASE_URL": base_url,
            "NVIDIA_TANNER_MODEL": modelo,
        }.items()
        if not valor
    ]
    if faltantes:
        raise RuntimeError("Configuración incompleta: " + ", ".join(faltantes))

    return ConfiguracionTanner(api_key=api_key, base_url=base_url, modelo=modelo)


class ClienteNvidiaInterpreting:
    """Cliente real — hace una llamada de red real a NVIDIA en cada uso.

    Reintenta hasta _INTENTOS_MAXIMOS veces ante fallos transitorios
    (timeouts, sobrecarga del servicio, errores de conexión) antes de
    reportar el fallo. No reintenta si el modelo respondió pero con un
    JSON malformado en TODOS los intentos — eso sí se reporta tal cual,
    porque insistir indefinidamente ante una falla de formato consistente
    no aporta nada.
    """

    def __init__(self, configuracion: ConfiguracionTanner | None = None) -> None:
        self.configuracion = configuracion or cargar_configuracion_tanner()
        self._cliente = OpenAI(
            api_key=self.configuracion.api_key,
            base_url=self.configuracion.base_url,
            max_retries=0,
        )

    def identificar_conceptos_y_relaciones(
        self,
        texto_interpretacion: str,
        conceptos_minimos: tuple[str, ...],
        relaciones_esperadas: tuple[str, ...],
    ) -> RespuestaClienteLLM:
        solicitud = (
            f"Conceptos posibles: {list(conceptos_minimos)}\n"
            f"Relaciones posibles: {list(relaciones_esperadas)}\n\n"
            f"Texto del estudiante:\n{texto_interpretacion}"
        )

        ultimo_error: str = "sin detalle disponible"

        for intento in range(1, _INTENTOS_MAXIMOS + 1):
            try:
                respuesta = self._cliente.chat.completions.create(
                    model=self.configuracion.modelo,
                    messages=[
                        {"role": "system", "content": _PROMPT_SISTEMA},
                        {"role": "user", "content": solicitud},
                    ],
                    timeout=30.0,
                    max_tokens=500,
                    temperature=0.0,
                )
                contenido = respuesta.choices[0].message.content or ""
                datos = json.loads(contenido)

                return RespuestaClienteLLM(
                    conceptos_detectados=tuple(datos.get("conceptos_detectados", [])),
                    relaciones_detectadas=tuple(datos.get("relaciones_detectadas", [])),
                    exitosa=True,
                )
            except json.JSONDecodeError as error:
                ultimo_error = f"El modelo no devolvió JSON válido: {error}"
            except Exception as error:  # noqa: BLE001 — cualquier fallo de red/API se reporta, no se oculta
                ultimo_error = f"{type(error).__name__}: {error}"

            if intento < _INTENTOS_MAXIMOS:
                time.sleep(_ESPERA_ENTRE_INTENTOS_SEGUNDOS)

        return RespuestaClienteLLM(
            conceptos_detectados=(),
            relaciones_detectadas=(),
            exitosa=False,
            detalle_error=f"Tras {_INTENTOS_MAXIMOS} intentos: {ultimo_error}",
        )
