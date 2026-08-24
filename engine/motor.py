"""
Módulo extraído de app.py v19 (KIKE-NNN) como parte de la separación
Datos -> Hallazgos -> Riesgos -> Diagnosticos -> NOC/NIC.

Lógica de negocio verificada byte-a-byte contra el comportamiento original
mediante tests/test_golden.py antes de sustituir el código en app.py.
"""

import pandas as pd
from engine.evidencia import PolaridadEvidencia
from engine.parser_negaciones import conceptos_catalogo, parsear_texto_libre
from engine.texto import normalizar_texto, separar_lista


def calcular_puntaje(texto_clinico, fila):
    """
    Motor v17:
    - Exige al menos una característica definitoria para diagnósticos reales.
    - Pesa más lo definitorio que lo relacionado/asociado.
    - Etiqueta coincidencias para explicar el razonamiento.
    - Permite diagnósticos de riesgo cuando su etiqueta clave aparece en datos de riesgo.
    """
    caracteristicas = separar_lista(fila["caracteristicas"])
    relacionados = separar_lista(fila["relacionados"])
    asociados = separar_lista(fila["asociados"])
    vocabulario = list(dict.fromkeys(
        caracteristicas
        + relacionados
        + asociados
        + [str(fila.get("nanda", ""))]
    ))
    parsing = parsear_texto_libre(
        texto_clinico,
        vocabulario,
        origen="calcular_puntaje_legacy",
    )
    puntaje, coincidencias, _detalles = calcular_puntaje_evidencias(
        parsing.evidencias, fila
    )
    return puntaje, coincidencias


def _valor_enum(valor):
    return getattr(valor, "value", valor)


def _detalle_coincidencia(termino, categoria, evidencia):
    return {
        "termino": termino,
        "categoria": categoria,
        "fuente": _valor_enum(evidencia.fuente),
        "polaridad": _valor_enum(evidencia.polaridad),
        "origen": evidencia.origen,
        "derivada_de": evidencia.derivada_de,
        "inicio": evidencia.inicio,
        "fin": evidencia.fin,
    }


def calcular_puntaje_evidencias(evidencias, fila):
    """Calcula el score heredado usando solo evidencia positiva confiable."""
    por_concepto = {}
    for evidencia in evidencias:
        if evidencia.puntuable:
            por_concepto.setdefault(normalizar_texto(evidencia.concepto), []).append(evidencia)

    grupos = (
        ("DEF", separar_lista(fila["caracteristicas"]), 4),
        ("REL", separar_lista(fila["relacionados"]), 2),
        ("ASO", separar_lista(fila["asociados"]), 1),
    )
    detalles = []
    terminos_por_categoria = {"DEF": [], "REL": [], "ASO": []}
    for categoria, terminos, _peso in grupos:
        for termino in terminos:
            productores = por_concepto.get(normalizar_texto(termino), [])
            if productores:
                terminos_por_categoria[categoria].append(termino)
                detalles.extend(
                    _detalle_coincidencia(termino, categoria, evidencia)
                    for evidencia in productores
                )

    nombre_nanda = normalizar_texto(fila.get("nanda", ""))
    if not terminos_por_categoria["DEF"] and "riesgo" in nombre_nanda:
        productores = por_concepto.get(nombre_nanda, [])
        if productores:
            termino = str(fila.get("nanda", "")).lower()
            terminos_por_categoria["DEF"].append(termino)
            detalles.extend(
                _detalle_coincidencia(termino, "DEF", evidencia)
                for evidencia in productores
            )

    if not terminos_por_categoria["DEF"]:
        return 0, [], []

    puntaje = (
        len(terminos_por_categoria["DEF"]) * 4
        + len(terminos_por_categoria["REL"]) * 2
        + len(terminos_por_categoria["ASO"]) * 1
    )
    coincidencias = [
        f"[{categoria}] {termino}"
        for categoria in ("DEF", "REL", "ASO")
        for termino in terminos_por_categoria[categoria]
    ]
    return puntaje, coincidencias, detalles


def detectar_contradicciones(evidencias):
    """Conserva, sin resolver, conceptos presentes con ambas polaridades."""
    positivas = {
        normalizar_texto(e.concepto) for e in evidencias if e.puntuable
    }
    negadas = {
        normalizar_texto(e.concepto)
        for e in evidencias
        if _valor_enum(e.polaridad) == PolaridadEvidencia.NEGADA.value
    }
    return sorted(positivas & negadas)


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
    evidencias=None,
):
    resultados = []
    estado_parsing = "NO_APLICA"
    if evidencias is None:
        parsing = parsear_texto_libre(
            texto_clinico, conceptos_catalogo(nanda_df), origen="api_legacy"
        )
        evidencias = list(parsing.evidencias)
        estado_parsing = parsing.estado
    else:
        evidencias = list(evidencias)

    conceptos_positivos = {
        normalizar_texto(e.concepto) for e in evidencias if e.puntuable
    }
    dolor_observado = any(
        normalizar_texto(termino) in conceptos_positivos
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
        puntaje, coincidencias, detalles = calcular_puntaje_evidencias(evidencias, fila)

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
            detalles = [
                detalle for detalle in detalles
                if f"[{detalle['categoria']}] {detalle['termino']}" in coincidencias
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
                "Coincidencias estructuradas": detalles,
                "Puntaje": puntaje,
                "Confianza": nivel_confianza(puntaje),
                "NOC sugerido": noc,
                "NIC sugerido": nic,
                "Prioridad": prioridad,
                "Jerarquía": "Principal" if puntaje >= 9 else "Complementario",
                "Nota": "Requiere validación clínica"
            })

    contradicciones = detectar_contradicciones(evidencias)
    atributos = {
        "evidencias": evidencias,
        "contradicciones": contradicciones,
        "advertencia_evidencia": (
            "Existen datos contradictorios que requieren revisión."
            if contradicciones else ""
        ),
        "estado_parsing": estado_parsing,
    }
    if not resultados:
        vacio = pd.DataFrame()
        vacio.attrs.update(atributos)
        return vacio

    df = pd.DataFrame(resultados)
    df = df.sort_values(by="Puntaje", ascending=False)
    df = df[df["Puntaje"] >= 8]
    df = df.head(10)
    df.attrs.update(atributos)

    return df
