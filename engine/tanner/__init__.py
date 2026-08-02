"""Motor pedagógico basado en el Modelo de Juicio Clínico de Tanner."""

from engine.tanner.casos import CasoTanner, cargar_caso_tanner
from engine.tanner.modelos import (
    CategoriaIndicio,
    IndicioTanner,
    ResultadoNoticing,
)
from engine.tanner.noticing import evaluar_noticing
from engine.tanner.servicio import EjecucionNoticing, ejecutar_noticing_desde_caso

from engine.tanner.retroalimentacion import (
    RetroalimentacionNoticing,
    generar_retroalimentacion_noticing,
)

# Nota deliberada: engine.tanner.cliente_llm NO se importa aquí.
# interpreting.py define solo el contrato (Protocol) y la lógica pura;
# el cliente real de NVIDIA depende de paquetes externos (openai,
# python-dotenv) y de .env.tanner. Si se importara aquí, cualquier
# `import engine.tanner` fallaría en un entorno sin esas dependencias
# instaladas — incluido Streamlit Cloud, donde Tanner aún no está
# conectado a app.py. Quien necesite el cliente real debe importarlo
# explícitamente desde engine.tanner.cliente_llm.
from engine.tanner.interpreting import (
    ClienteInterpretacion,
    RespuestaClienteLLM,
    ResultadoInterpreting,
    evaluar_interpreting,
)
from engine.tanner.retroalimentacion_interpreting import (
    RetroalimentacionInterpreting,
    generar_retroalimentacion_interpreting,
)

__all__ = [
    "generar_retroalimentacion_noticing",
    "RetroalimentacionNoticing",
    "ejecutar_noticing_desde_caso",
    "EjecucionNoticing",
    "CasoTanner",
    "cargar_caso_tanner",
    "CategoriaIndicio",
    "IndicioTanner",
    "ResultadoNoticing",
    "evaluar_noticing",
    "ClienteInterpretacion",
    "RespuestaClienteLLM",
    "ResultadoInterpreting",
    "evaluar_interpreting",
    "RetroalimentacionInterpreting",
    "generar_retroalimentacion_interpreting",
]
