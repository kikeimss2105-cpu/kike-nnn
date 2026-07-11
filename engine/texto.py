"""
Módulo extraído de app.py v19 (KIKE-NNN) como parte de la separación
Datos -> Hallazgos -> Riesgos -> Diagnosticos -> NOC/NIC.

Lógica de negocio verificada byte-a-byte contra el comportamiento original
mediante tests/test_golden.py antes de sustituir el código en app.py.
"""

import pandas as pd


def separar_lista(texto):
    if pd.isna(texto):
        return []
    return [item.strip().lower() for item in str(texto).split(";") if item.strip()]


def normalizar_texto(texto):
    if texto is None:
        return ""
    texto = str(texto).lower()
    reemplazos = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ü": "u", "ñ": "ñ"
    }
    for original, nuevo in reemplazos.items():
        texto = texto.replace(original, nuevo)
    return texto


def consolidar_hallazgos(*listas_hallazgos):
    """Combina múltiples listas de hallazgos (checkboxes, escalas, rutas
    obstétricas, Gordon, etc.) en una sola lista deduplicada, preservando
    el orden de primera aparición.

    Existe como función explícita (en vez de la concatenación inline que
    vivía en app.py) para que la integración de una nueva fuente de
    hallazgos — como ocurrió con Gordon, que quedó fuera de esta lista
    varias semanas sin que ningún test lo detectara — quede cubierta por
    golden tests. Si mañana se agrega una fuente nueva y se olvida pasarla
    aquí, seguirá sin detectarse automáticamente: lo que este test SÍ
    garantiza es que las fuentes ya conectadas nunca se vuelvan a desconectar
    silenciosamente."""
    combinado = []
    for lista in listas_hallazgos:
        combinado += (lista or [])
    return list(dict.fromkeys(combinado))
