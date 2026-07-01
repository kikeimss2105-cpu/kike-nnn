"""
Módulo extraído de app.py v19 (KIKE-NNN) como parte de la separación
Datos -> Hallazgos -> Riesgos -> Diagnosticos -> NOC/NIC.

Lógica de negocio verificada byte-a-byte contra el comportamiento original
mediante tests/test_golden.py antes de sustituir el código en app.py.
"""


def obtener_indicadores_noc(noc_texto, noc_indicadores_df):
    if not noc_texto or noc_texto == "Sin NOC vinculado":
        return "Sin indicadores NOC vinculados"

    nocs = [x.strip() for x in str(noc_texto).split("|")]
    lineas = []

    for noc in nocs:
        sub = noc_indicadores_df[noc_indicadores_df["noc"] == noc]
        if not sub.empty:
            indicadores = [
                f"- {row['indicador']} ({row['escala_sugerida']})"
                for _, row in sub.iterrows()
            ]
            lineas.append(f"{noc}:\n" + "\n".join(indicadores))

    return "\n\n".join(lineas) if lineas else "Sin indicadores NOC vinculados"


def obtener_actividades_nic(nic_texto, nic_actividades_df):
    if not nic_texto or nic_texto == "Sin NIC vinculado":
        return "Sin actividades NIC vinculadas"

    nics = [x.strip() for x in str(nic_texto).split("|")]
    lineas = []

    for nic in nics:
        sub = nic_actividades_df[nic_actividades_df["nic"] == nic]
        if not sub.empty:
            actividades = [
                f"- [{row['tipo']}] {row['actividad']}"
                for _, row in sub.iterrows()
            ]
            lineas.append(f"{nic}:\n" + "\n".join(actividades))

    return "\n\n".join(lineas) if lineas else "Sin actividades NIC vinculadas"


def obtener_fundamentos_nic(nic_texto, fundamentos_df):
    if not nic_texto or nic_texto == "Sin NIC vinculado":
        return "Sin fundamentos vinculados"

    nics = [x.strip() for x in str(nic_texto).split("|")]
    lineas = []

    for nic in nics:
        sub = fundamentos_df[fundamentos_df["nic"] == nic]
        if not sub.empty:
            for _, row in sub.iterrows():
                lineas.append(f"- {nic}: {row['fundamento']}")

    return "\n".join(lineas) if lineas else "Sin fundamentos vinculados"


def obtener_meta_nanda(nanda_nombre, metas_df):
    sub = metas_df[metas_df["nanda"] == nanda_nombre]
    if sub.empty:
        return "Meta pendiente de individualizar según valoración clínica."
    return str(sub.iloc[0]["meta"])


def enriquecer_plan(df_resultados, metas_df, noc_indicadores_df, nic_actividades_df, fundamentos_df):
    if df_resultados.empty:
        return df_resultados

    df = df_resultados.copy()
    df["Meta esperada"] = df["NANDA"].apply(lambda x: obtener_meta_nanda(x, metas_df))
    df["Indicadores NOC"] = df["NOC sugerido"].apply(lambda x: obtener_indicadores_noc(x, noc_indicadores_df))
    df["Actividades NIC"] = df["NIC sugerido"].apply(lambda x: obtener_actividades_nic(x, nic_actividades_df))
    df["Fundamentos"] = df["NIC sugerido"].apply(lambda x: obtener_fundamentos_nic(x, fundamentos_df))
    return df
