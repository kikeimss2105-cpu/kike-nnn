"""
Módulo extraído de app.py v19 (KIKE-NNN) como parte de la separación
Datos -> Hallazgos -> Riesgos -> Diagnosticos -> NOC/NIC.

Lógica de negocio verificada byte-a-byte contra el comportamiento original
mediante tests/test_golden.py antes de sustituir el código en app.py.
"""

import pandas as pd


def construir_criterios_nanda(nanda_df):
    """Arma, por código NANDA, la lista de criterios clínicos (características
    definitorias + factores relacionados) que el estudiante puede elegir como
    sustento de su decisión en el módulo de razonamiento clínico."""
    criterios = {}
    for _, fila in nanda_df.iterrows():
        opciones = []
        for campo in ["caracteristicas", "relacionados"]:
            valor = fila.get(campo, "")
            if pd.notna(valor) and str(valor).strip():
                opciones += [x.strip() for x in str(valor).split(";") if x.strip()]
        criterios[fila["codigo"]] = sorted(set(opciones))
    return criterios
