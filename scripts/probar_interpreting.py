"""Prueba manual de Interpreting contra el modelo NVIDIA REAL.

A diferencia de tests/tanner/test_interpreting.py (que usa un cliente
simulado, sin red, determinista), este script SÍ llama a NVIDIA de
verdad. Sirve para ver con casos reales qué tan bien el modelo
configurado (NVIDIA_TANNER_MODEL en .env.tanner) reconoce conceptos y
relaciones en texto libre — antes de conectar Interpreting a cualquier
interfaz real.

No es determinista: cada corrida puede dar resultados ligeramente
distintos (aunque temperature=0.0 en cliente_llm.py debería mantenerlo
razonablemente estable). No es una prueba automatizada — es una
inspección manual con salida legible.

Requiere .env.tanner configurado con NVIDIA_TANNER_KEY, NVIDIA_BASE_URL
y NVIDIA_TANNER_MODEL. Hace llamadas de red reales — tiene costo.

Uso:
    cd ~/ProyectosIA/kike-nnn-v19
    source venv/bin/activate
    python scripts/probar_interpreting.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.tanner.casos import cargar_caso_tanner
from engine.tanner.interpreting import evaluar_interpreting
from engine.tanner.retroalimentacion_interpreting import (
    generar_retroalimentacion_interpreting,
)

CASO = Path(__file__).resolve().parent.parent / "data" / "casos" / "OBS-HTA-001.yaml"

CASOS_DE_PRUEBA = {
    "COMPLETA (debería reconocer casi todo)": (
        "La paciente está embarazada y tiene la presión muy alta, lo cual "
        "es grave. Además tiene un dolor de cabeza fuerte y ve borroso, "
        "que son señales de que algo neurológico está pasando. Esto puede "
        "empeorar rápido y pone en riesgo su salud, por lo que necesita "
        "que la valoren y atiendan de inmediato."
    ),
    "PARCIAL (menciona hipertensión y embarazo, omite lo neurológico)": (
        "La señora tiene la presión muy alta y tiene 36 semanas de "
        "embarazo."
    ),
    "FUERA DE TEMA (no debería reconocer casi nada)": (
        "La paciente se ve preocupada y pregunta varias veces por su "
        "pareja, quiere saber si ya llegó al hospital."
    ),
    "VACÍA (no debería llamar a la red)": "",
}


def main() -> None:
    print("=" * 70)
    print("PRUEBA MANUAL DE INTERPRETING CONTRA NVIDIA REAL")
    print("=" * 70)

    try:
        from engine.tanner.cliente_llm import (
            ClienteNvidiaInterpreting,
            cargar_configuracion_tanner,
        )

        configuracion = cargar_configuracion_tanner()
    except RuntimeError as error:
        print(f"\n[ERROR DE CONFIGURACIÓN] {error}")
        print("Revisa que exista .env.tanner con las 3 variables requeridas.")
        return
    except ImportError as error:
        print(f"\n[ERROR DE DEPENDENCIAS] {error}")
        print("Corre: pip install -r requirements.txt")
        return

    print(f"\nModelo configurado: {configuracion.modelo}")
    print(f"Base URL: {configuracion.base_url}")

    caso = cargar_caso_tanner(CASO)
    print(f"\nCaso: {caso.id} — {caso.titulo}")
    print(f"Conceptos esperados ({len(caso.conceptos_minimos_interpreting)}): "
          f"{caso.conceptos_minimos_interpreting}")
    print(f"Relaciones esperadas ({len(caso.relaciones_esperadas_interpreting)}): "
          f"{caso.relaciones_esperadas_interpreting}")

    cliente = ClienteNvidiaInterpreting(configuracion)

    for etiqueta, texto in CASOS_DE_PRUEBA.items():
        print("\n" + "-" * 70)
        print(f"CASO DE PRUEBA: {etiqueta}")
        print(f"Texto: {texto!r}" if texto else "Texto: (vacío)")
        print("-" * 70)

        resultado = evaluar_interpreting(
            caso.conceptos_minimos_interpreting,
            caso.relaciones_esperadas_interpreting,
            texto,
            cliente=cliente,
        )

        retro = generar_retroalimentacion_interpreting(caso, resultado, texto)
        print(retro.como_texto())

        if not resultado.evaluacion_confiable:
            print(f"\n[AVISO] Evaluación no confiable: {resultado.detalle_error}")

    print("\n" + "=" * 70)
    print("FIN DE LA PRUEBA")
    print("=" * 70)


if __name__ == "__main__":
    main()
