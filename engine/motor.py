"""
Módulo extraído de app.py v19 (KIKE-NNN) como parte de la separación
Datos -> Hallazgos -> Riesgos -> Diagnosticos -> NOC/NIC.

Lógica de negocio verificada byte-a-byte contra el comportamiento original
mediante tests/test_golden.py antes de sustituir el código en app.py.
"""

import pandas as pd
from engine.texto import normalizar_texto, separar_lista


def calcular_puntaje(texto_clinico, fila):
    """
    Motor v17:
    - Exige al menos una característica definitoria para diagnósticos reales.
    - Pesa más lo definitorio que lo relacionado/asociado.
    - Etiqueta coincidencias para explicar el razonamiento.
    - Permite diagnósticos de riesgo cuando su etiqueta clave aparece en datos de riesgo.
    """
    texto = normalizar_texto(texto_clinico)

    caracteristicas = separar_lista(fila["caracteristicas"])
    relacionados = separar_lista(fila["relacionados"])
    asociados = separar_lista(fila["asociados"])

    caracteristicas_norm = [(x, normalizar_texto(x)) for x in caracteristicas]
    relacionados_norm = [(x, normalizar_texto(x)) for x in relacionados]
    asociados_norm = [(x, normalizar_texto(x)) for x in asociados]

    coincidencias_caracteristicas = [original for original, norm in caracteristicas_norm if norm and norm in texto]
    coincidencias_relacionados = [original for original, norm in relacionados_norm if norm and norm in texto]
    coincidencias_asociados = [original for original, norm in asociados_norm if norm and norm in texto]

    nombre_nanda = normalizar_texto(fila.get("nanda", ""))

    # Para diagnósticos de riesgo, algunas bases usan la señal de riesgo como característica.
    # Si el usuario ingresó literalmente el diagnóstico/riesgo, cuenta como dato definitorio educativo.
    if not coincidencias_caracteristicas and "riesgo" in nombre_nanda:
        etiqueta_riesgo = normalizar_texto(str(fila.get("nanda", "")))
        if etiqueta_riesgo in texto:
            coincidencias_caracteristicas.append(str(fila.get("nanda", "")).lower())

    # Regla crítica: sin característica definitoria no se sugiere diagnóstico.
    # Esto reduce falsos positivos por factores aislados.
    if not coincidencias_caracteristicas:
        return 0, []

    puntaje = (
        len(coincidencias_caracteristicas) * 4
        + len(coincidencias_relacionados) * 2
        + len(coincidencias_asociados) * 1
    )

    coincidencias_totales = (
        [f"[DEF] {x}" for x in coincidencias_caracteristicas]
        + [f"[REL] {x}" for x in coincidencias_relacionados]
        + [f"[ASO] {x}" for x in coincidencias_asociados]
    )

    return puntaje, coincidencias_totales


def nivel_confianza(puntaje):
    if puntaje >= 12:
        return "Alta"
    elif puntaje >= 8:
        return "Media"
    elif puntaje > 0:
        return "Baja"
    return "Sin coincidencia"


def buscar_diagnosticos(
    texto_clinico,
    nanda_df,
    enlaces_df,
    *,
    dato_fetal_referido=False,
):
    resultados = []
    texto_normalizado = normalizar_texto(texto_clinico)
    dolor_observado = any(
        termino in texto_normalizado
        for termino in (
            "dolor de parto",
            "dolor abdominal",
            "dolor uterino",
            "contracciones dolorosas",
        )
    )

    for _, fila in nanda_df.iterrows():
        nombre_nanda = normalizar_texto(fila.get("nanda", ""))
        if "materno-fetal" in nombre_nanda and not dato_fetal_referido:
            continue
        if nombre_nanda == "dolor de parto" and not dolor_observado:
            continue
        puntaje, coincidencias = calcular_puntaje(texto_clinico, fila)

        # El perfil obstétrico y su vigilancia son contexto derivado, no tres
        # evidencias clínicas independientes para reforzar la sugerencia 00209.
        if nombre_nanda == "riesgo de alteracion de la diada materno-fetal":
            contexto_derivado = {
                "[ASO] embarazo mayor de 20 semanas",
                "[ASO] paciente obstétrica",
                "[ASO] vigilancia obstétrica",
            }
            coincidencias = [
                coincidencia
                for coincidencia in coincidencias
                if coincidencia not in contexto_derivado
            ]
            puntaje = sum(
                4 if coincidencia.startswith("[DEF]")
                else 2 if coincidencia.startswith("[REL]")
                else 1
                for coincidencia in coincidencias
            )

        if puntaje > 0:
            enlaces = enlaces_df[enlaces_df["nanda"] == fila["nanda"]]

            if enlaces.empty:
                noc = "Sin NOC vinculado"
                nic = "Sin NIC vinculado"
                prioridad = "No definida"
            else:
                noc = " | ".join(enlaces["noc"].unique())
                nic = " | ".join(enlaces["nic"].unique())
                prioridad = " | ".join(enlaces["prioridad"].unique())

            resultados.append({
                "Código": fila["codigo"],
                "Dominio": fila["dominio"],
                "Clase": fila["clase"],
                "NANDA": fila["nanda"],
                "Definición": fila["definicion"],
                "Coincidencias": ", ".join(coincidencias),
                "Puntaje": puntaje,
                "Confianza": nivel_confianza(puntaje),
                "NOC sugerido": noc,
                "NIC sugerido": nic,
                "Prioridad": prioridad,
                "Jerarquía": "Principal" if puntaje >= 9 else "Complementario",
                "Nota": "Requiere validación clínica"
            })

    if not resultados:
        return pd.DataFrame()

    df = pd.DataFrame(resultados)
    df = df.sort_values(by="Puntaje", ascending=False)
    df = df[df["Puntaje"] >= 8]
    df = df.head(10)

    return df
