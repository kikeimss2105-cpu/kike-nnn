import streamlit as st
import pandas as pd
from utils.exportadores import generar_excel, generar_word

st.set_page_config(page_title="KIKE-NNN | Apoyo al razonamiento clínico", layout="wide")


# =========================
# DISCLAIMER CLÍNICO — BLOQUEO TOTAL HASTA ACEPTACIÓN
# =========================
def _mostrar_disclaimer():
    if st.session_state.get("disclaimer_ok"):
        return

    st.markdown("""
    <style>
    .disclaimer-box {
        background-color: #fff8e1;
        border-left: 5px solid #f0a500;
        padding: 1.2rem 1.5rem;
        border-radius: 6px;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.image("https://img.shields.io/badge/KIKE--NNN-v18.1-blue?style=flat-square", width=160)
    st.markdown("## ⚕️ Aviso de uso obligatorio")

    st.markdown("""
<div class="disclaimer-box">

**KIKE-NNN es una herramienta exclusivamente educativa de apoyo al razonamiento clínico en enfermería.**

Antes de continuar, lee y acepta los siguientes términos:

- **No emite diagnósticos de enfermería definitivos** ni diagnósticos médicos de ningún tipo.
- **No sustituye** el juicio clínico del profesional o estudiante de enfermería.
- **No reemplaza** protocolos institucionales vigentes (GPC-IMSS, ACOG, NOM, guías locales).
- Las rutas clínicas generadas (hipertensiva, RPM, hemorrágica, etc.) son **guías educativas orientativas**, no órdenes clínicas.
- El profesional o estudiante es **el único responsable** de validar toda salida con fuentes autorizadas y con valoración directa del paciente.
- Esta herramienta **no está certificada por COFEPRIS** ni por ningún organismo regulatorio sanitario nacional o internacional.
- **No almacena ni transmite datos de pacientes.** Todo el procesamiento ocurre localmente en esta sesión.

</div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    col1, col2 = st.columns([4, 1])
    with col1:
        st.caption("Al continuar, confirmas que entiendes que esta herramienta tiene uso educativo y que el criterio clínico profesional prevalece sobre cualquier resultado generado.")
    with col2:
        if st.button("✓ Acepto — continuar", type="primary", use_container_width=True):
            st.session_state.disclaimer_ok = True
            st.rerun()

    st.stop()


_mostrar_disclaimer()


st.title("🩺 KIKE-NNN | Sistema educativo NANDA-NIC-NOC")
st.subheader("Motor de razonamiento clínico con perfil de paciente y módulo obstétrico ajustado")

st.sidebar.success("KIKE-NNN v18.1 | Ajuste fino obstétrico")
st.sidebar.info("Rutas: hipertensiva, RPM/infección, dolor obstétrico, hemorrágica y bienestar fetal.")


# =========================
# CARGA DE BASES CSV
# =========================

@st.cache_data
def cargar_datos():
    nanda = pd.read_csv("data/nanda.csv", dtype={"codigo": str})
    enlaces = pd.read_csv("data/enlaces.csv")
    noc_indicadores = pd.read_csv("data/noc_indicadores.csv")
    nic_actividades = pd.read_csv("data/nic_actividades.csv")
    fundamentos = pd.read_csv("data/fundamentos.csv")
    metas = pd.read_csv("data/metas.csv")
    nanda["codigo"] = nanda["codigo"].str.zfill(5)
    return nanda, enlaces, noc_indicadores, nic_actividades, fundamentos, metas


nanda_df, enlaces_df, noc_indicadores_df, nic_actividades_df, fundamentos_df, metas_df = cargar_datos()


@st.cache_data
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


nanda_criterios = construir_criterios_nanda(nanda_df)


# =========================
# MOTOR DE PUNTUACIÓN
# =========================


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


def buscar_diagnosticos(texto_clinico):
    resultados = []

    for _, fila in nanda_df.iterrows():
        puntaje, coincidencias = calcular_puntaje(texto_clinico, fila)

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



def obtener_indicadores_noc(noc_texto):
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


def obtener_actividades_nic(nic_texto):
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


def obtener_fundamentos_nic(nic_texto):
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


def obtener_meta_nanda(nanda_nombre):
    sub = metas_df[metas_df["nanda"] == nanda_nombre]
    if sub.empty:
        return "Meta pendiente de individualizar según valoración clínica."
    return str(sub.iloc[0]["meta"])


def enriquecer_plan(df_resultados):
    if df_resultados.empty:
        return df_resultados

    df = df_resultados.copy()
    df["Meta esperada"] = df["NANDA"].apply(obtener_meta_nanda)
    df["Indicadores NOC"] = df["NOC sugerido"].apply(obtener_indicadores_noc)
    df["Actividades NIC"] = df["NIC sugerido"].apply(obtener_actividades_nic)
    df["Fundamentos"] = df["NIC sugerido"].apply(obtener_fundamentos_nic)
    return df


def interpretar_braden(puntaje_braden):
    if puntaje_braden <= 9:
        return "Riesgo muy alto"
    elif puntaje_braden <= 12:
        return "Riesgo alto"
    elif puntaje_braden <= 14:
        return "Riesgo moderado"
    elif puntaje_braden <= 18:
        return "Riesgo leve"
    return "Sin riesgo significativo"


def interpretar_eva(eva):
    if eva == 0:
        return "Sin dolor"
    elif eva <= 3:
        return "Dolor leve"
    elif eva <= 6:
        return "Dolor moderado"
    return "Dolor intenso"


def interpretar_glasgow(glasgow):
    if glasgow <= 8:
        return "Compromiso neurológico grave"
    elif glasgow <= 12:
        return "Compromiso neurológico moderado"
    elif glasgow <= 14:
        return "Compromiso neurológico leve"
    return "Estado neurológico aparentemente conservado"


def interpretar_riesgo_caidas(puntaje):
    if puntaje >= 6:
        return "Riesgo alto de caídas"
    elif puntaje >= 3:
        return "Riesgo moderado de caídas"
    elif puntaje >= 1:
        return "Riesgo bajo de caídas"
    return "Sin riesgo evidente por este tamizaje"


def interpretar_spo2(spo2):
    if spo2 <= 90:
        return "Saturación críticamente baja"
    elif spo2 <= 93:
        return "Saturación baja"
    elif spo2 <= 95:
        return "Saturación en vigilancia"
    return "Saturación dentro de rango esperado"


def interpretar_fr_adulto(fr):
    if fr < 12:
        return "Bradipnea"
    elif fr <= 20:
        return "Frecuencia respiratoria dentro de rango adulto esperado"
    elif fr <= 30:
        return "Taquipnea"
    return "Taquipnea marcada"


def interpretar_fr_por_tipo(fr, tipo_paciente):
    """Interpretación educativa de FR según perfil. Ajustar siempre a edad exacta y protocolo."""
    if tipo_paciente == "Recién nacido":
        if fr < 30:
            return "Bradipnea para recién nacido"
        elif fr <= 60:
            return "Frecuencia respiratoria dentro de rango esperado para recién nacido"
        return "Taquipnea en recién nacido"

    if tipo_paciente == "Pediátrico":
        if fr < 20:
            return "FR baja o en vigilancia para paciente pediátrico"
        elif fr <= 30:
            return "Frecuencia respiratoria dentro de rango pediátrico general"
        elif fr <= 40:
            return "Taquipnea pediátrica"
        return "Taquipnea pediátrica marcada"

    if tipo_paciente == "Obstétrico":
        if fr < 12:
            return "Bradipnea"
        elif fr <= 20:
            return "FR dentro de rango adulto esperado en obstetricia"
        elif fr <= 24:
            return "FR en vigilancia obstétrica"
        return "Taquipnea: valorar signos de alarma obstétrica"

    if tipo_paciente == "Geriátrico":
        if fr < 12:
            return "Bradipnea"
        elif fr <= 20:
            return "FR dentro de rango esperado en adulto mayor"
        elif fr <= 28:
            return "Taquipnea en adulto mayor"
        return "Taquipnea marcada en adulto mayor"

    return interpretar_fr_adulto(fr)


def recomendaciones_por_tipo(tipo_paciente):
    recomendaciones = {
        "Adulto": "Perfil adulto: Braden, EVA, Glasgow, caídas y respiratorio general disponibles.",
        "Geriátrico": "Perfil geriátrico: prioriza caídas, Braden, movilidad, piel, nutrición e infección.",
        "Pediátrico": "Perfil pediátrico: usar con cautela. Ajustar signos vitales a edad exacta y protocolo.",
        "Obstétrico": "Perfil obstétrico: vigilar PA, sangrado, dolor, cefalea, fosfenos, edema, RPM y movimientos fetales según protocolo.",
        "Recién nacido": "Perfil RN: requiere módulos específicos APGAR, Silverman-Andersen y Capurro para mayor precisión."
    }
    return recomendaciones.get(tipo_paciente, "Perfil no especificado.")



def interpretar_pa_obstetrica(pas, pad, semanas_gestacion):
    """Interpretación educativa. No diagnostica; orienta vigilancia obstétrica."""
    if pas >= 160 or pad >= 110:
        return "PA en rango severo: requiere valoración urgente según protocolo obstétrico"
    if pas >= 140 or pad >= 90:
        if semanas_gestacion >= 20:
            return "PA elevada desde semana 20 o más: vigilar datos compatibles con trastorno hipertensivo del embarazo"
        return "PA elevada en embarazo: requiere vigilancia y validación clínica"
    if pas >= 130 or pad >= 80:
        return "PA en vigilancia: repetir medición y valorar contexto clínico"
    return "PA dentro de rango esperado por este tamizaje"


def generar_alertas_obstetricas(
    tipo_paciente,
    semanas_gestacion,
    pas,
    pad,
    temperatura,
    cefalea_intensa,
    fosfenos,
    acufenos,
    epigastralgia,
    edema_cara_manos,
    convulsiones,
    sangrado_vaginal,
    salida_liquido,
    liquido_fetido,
    liquido_verdoso,
    dolor_abdominal_intenso,
    contracciones_antes_termino,
    disminucion_mov_fetales,
    nausea_vomito_persistente,
    disuria_obstetrica,
):
    alertas = []

    if tipo_paciente != "Obstétrico":
        return alertas

    datos_neuro = cefalea_intensa or fosfenos or acufenos or epigastralgia or edema_cara_manos

    if pas >= 160 or pad >= 110:
        alertas.append({
            "Nivel": "Alta",
            "Área": "Obstétrico / hipertensión",
            "Alerta": f"PA {pas}/{pad} mmHg en rango severo.",
            "Acción sugerida": "Repetir medición si procede, mantener vigilancia, valorar datos de severidad y notificar de inmediato según protocolo."
        })
    elif pas >= 140 or pad >= 90:
        nivel = "Alta" if semanas_gestacion >= 20 and datos_neuro else "Media"
        alertas.append({
            "Nivel": nivel,
            "Área": "Obstétrico / hipertensión",
            "Alerta": f"PA {pas}/{pad} mmHg elevada en paciente obstétrica.",
            "Acción sugerida": "Valorar cefalea, fosfenos, acúfenos, epigastralgia, edema, proteinuria si está indicada y protocolo institucional."
        })

    if convulsiones:
        alertas.append({
            "Nivel": "Alta",
            "Área": "Obstétrico / neurológico",
            "Alerta": "Convulsiones reportadas en paciente obstétrica.",
            "Acción sugerida": "Emergencia obstétrica: proteger vía aérea, seguridad de la paciente y activar protocolo institucional."
        })

    if cefalea_intensa and (fosfenos or acufenos or epigastralgia or edema_cara_manos):
        alertas.append({
            "Nivel": "Alta",
            "Área": "Obstétrico / signos de alarma",
            "Alerta": "Cefalea intensa asociada a síntomas visuales, auditivos, epigastralgia o edema.",
            "Acción sugerida": "Valorar trastorno hipertensivo del embarazo y notificar según protocolo."
        })

    if sangrado_vaginal:
        alertas.append({
            "Nivel": "Alta",
            "Área": "Obstétrico / sangrado",
            "Alerta": "Sangrado vaginal durante el embarazo.",
            "Acción sugerida": "Valorar cantidad, dolor, signos vitales, edad gestacional y activar ruta obstétrica según protocolo."
        })

    if salida_liquido:
        nivel = "Alta" if semanas_gestacion < 37 else "Media"
        alertas.append({
            "Nivel": nivel,
            "Área": "Obstétrico / salida de líquido",
            "Alerta": "Salida de líquido transvaginal compatible con posible ruptura de membranas.",
            "Acción sugerida": "Registrar hora, color, olor, cantidad, fiebre, dolor, movimientos fetales y referir/avisar según protocolo."
        })

    if liquido_fetido or liquido_verdoso or temperatura >= 38:
        alertas.append({
            "Nivel": "Alta",
            "Área": "Obstétrico / infección o sufrimiento fetal",
            "Alerta": "Fiebre, líquido fétido o líquido verdoso registrado.",
            "Acción sugerida": "Vigilar signos de infección, estado materno-fetal y notificar según protocolo."
        })

    if dolor_abdominal_intenso:
        alertas.append({
            "Nivel": "Alta",
            "Área": "Obstétrico / dolor abdominal",
            "Alerta": "Dolor abdominal intenso en paciente obstétrica.",
            "Acción sugerida": "Valorar sangrado, dinámica uterina, signos vitales, edad gestacional y protocolo de urgencia obstétrica."
        })

    if contracciones_antes_termino and semanas_gestacion < 37:
        alertas.append({
            "Nivel": "Media",
            "Área": "Obstétrico / parto pretérmino",
            "Alerta": "Contracciones antes de las 37 semanas.",
            "Acción sugerida": "Valorar frecuencia, duración, dolor, salida de líquido, sangrado y protocolo de amenaza de parto pretérmino."
        })

    if disminucion_mov_fetales and semanas_gestacion >= 20:
        alertas.append({
            "Nivel": "Alta",
            "Área": "Obstétrico / bienestar fetal",
            "Alerta": "Disminución o ausencia de movimientos fetales referida.",
            "Acción sugerida": "Valorar bienestar fetal y notificar según protocolo institucional."
        })

    if nausea_vomito_persistente:
        alertas.append({
            "Nivel": "Media",
            "Área": "Obstétrico / hidratación",
            "Alerta": "Náusea o vómito persistente.",
            "Acción sugerida": "Valorar tolerancia oral, signos de deshidratación, peso, diuresis y necesidad de referencia."
        })

    if disuria_obstetrica:
        alertas.append({
            "Nivel": "Media",
            "Área": "Obstétrico / urinario",
            "Alerta": "Dolor o molestia al orinar durante el embarazo.",
            "Acción sugerida": "Valorar datos urinarios, fiebre, dolor lumbar y seguimiento según protocolo."
        })

    return alertas


def evaluar_rutas_obstetricas(tipo_paciente, semanas_gestacion=0, pa_sistolica=0, pa_diastolica=0,
                              temperatura=36.5, cefalea=False, fosfenos=False, acufenos=False,
                              epigastralgia=False, edema=False, convulsiones=False,
                              sangrado=False, salida_liquido=False, liquido_fetido=False,
                              liquido_verdoso=False, dolor_abdominal=False,
                              contracciones=False, movimientos_fetales="No aplica / no valorado",
                              hallazgos_detectados=None):
    """
    Clasifica señales obstétricas por ruta educativa.
    v18.1:
    - Separa dolor obstétrico de hemorragia.
    - No activa ruta hemorrágica sin sangrado.
    - No inyecta sangrado/shock si el usuario no marcó sangrado.
    """
    if tipo_paciente != "Obstétrico":
        return [], "No aplica"

    hallazgos_detectados = hallazgos_detectados or []
    texto_hallazgos = " ".join([str(x).lower() for x in hallazgos_detectados])

    def tiene(*terminos):
        return any(str(t).lower() in texto_hallazgos for t in terminos)

    def tiene_exacto(*terminos):
        buscados = {str(t).lower().strip() for t in terminos}
        return any(str(h).lower().strip() in buscados for h in hallazgos_detectados)

    rutas = []
    datos = []

    # =========================
    # RUTA HIPERTENSIVA / PREECLAMPSIA
    # =========================
    datos_hipertensivos = []

    pa_elevada = semanas_gestacion >= 20 and (pa_sistolica >= 140 or pa_diastolica >= 90)
    pa_severa = pa_sistolica >= 160 or pa_diastolica >= 110

    if pa_elevada:
        datos_hipertensivos.append(f"PA {pa_sistolica}/{pa_diastolica} desde semana 20 o más")
    elif tiene("hipertensión", "hipertension", "preeclampsia"):
        datos_hipertensivos.append("hallazgos compatibles con hipertensión/preeclampsia")

    if pa_severa:
        datos_hipertensivos.append("PA severa")
    if cefalea or tiene("cefalea"):
        datos_hipertensivos.append("cefalea")
    if fosfenos or tiene("fosfenos", "visión borrosa", "vision borrosa"):
        datos_hipertensivos.append("fosfenos/visión borrosa")
    if acufenos or tiene("acúfenos", "acufenos"):
        datos_hipertensivos.append("acúfenos")
    if epigastralgia or tiene("epigastralgia", "dolor epigástrico", "dolor epigastrico"):
        datos_hipertensivos.append("epigastralgia")
    if edema or tiene("edema", "edema de cara", "edema de manos"):
        datos_hipertensivos.append("edema cara/manos")

    convulsiones_reales = bool(convulsiones) or tiene_exacto(
        "convulsiones", "convulsión", "convulsion", "crisis convulsiva", "eclampsia"
    )
    if convulsiones_reales:
        datos_hipertensivos.append("convulsiones")

    if datos_hipertensivos:
        nivel = "Crítica" if (pa_severa or convulsiones_reales) else "Alta"
        datos_hipertensivos = list(dict.fromkeys(datos_hipertensivos))

        rutas.append({
            "Ruta": "Hipertensiva / preeclampsia",
            "Nivel": nivel,
            "Datos activadores": ", ".join(datos_hipertensivos),
            "Acción educativa": "Valorar signos de severidad, proteinuria si procede, bienestar fetal y activar protocolo institucional."
        })
        datos.extend(["hipertensión", "preeclampsia", "signos de alarma obstétrica", "riesgo de alteración de la díada materno-fetal"])

    # =========================
    # RUTA RPM / INFECCIÓN
    # =========================
    datos_rpm = []
    if salida_liquido or tiene("salida de líquido", "salida de liquido", "ruptura de membranas", "rpm"):
        datos_rpm.append("salida de líquido transvaginal")
    if liquido_fetido or tiene("líquido fétido", "liquido fetido", "mal olor"):
        datos_rpm.append("líquido fétido")
    if liquido_verdoso or tiene("líquido verdoso", "liquido verdoso", "meconio"):
        datos_rpm.append("líquido verdoso")
    if temperatura >= 38 or tiene("fiebre"):
        datos_rpm.append(f"fiebre {temperatura}°C" if temperatura >= 38 else "fiebre")
    if dolor_abdominal or tiene("dolor uterino", "dolor abdominal"):
        datos_rpm.append("dolor abdominal/uterino")

    if datos_rpm:
        nivel = "Alta" if (
            liquido_fetido or temperatura >= 38 or liquido_verdoso or
            tiene("líquido fétido", "liquido fetido", "fiebre", "líquido verdoso", "liquido verdoso")
        ) else "Media"
        datos_rpm = list(dict.fromkeys(datos_rpm))
        rutas.append({
            "Ruta": "RPM / infección",
            "Nivel": nivel,
            "Datos activadores": ", ".join(datos_rpm),
            "Acción educativa": "Vigilar temperatura, características del líquido, dolor, bienestar fetal y riesgo infeccioso según protocolo."
        })
        datos.extend([
            "salida de líquido transvaginal",
            "ruptura de membranas",
            "riesgo de infección",
            "vigilancia obstétrica",
            "riesgo de infección materno-fetal"
        ])

    # =========================
    # RUTA HEMORRÁGICA
    # Solo si hay sangrado real o explícitamente detectado.
    # =========================
    datos_hemorragicos = []
    sangrado_real = bool(sangrado) or tiene_exacto("sangrado vaginal", "hemorragia", "sangrado obstétrico")
    if sangrado_real:
        datos_hemorragicos.append("sangrado vaginal")
        if dolor_abdominal or tiene("dolor abdominal", "dolor uterino"):
            datos_hemorragicos.append("dolor abdominal")
        if (contracciones and semanas_gestacion < 37) or tiene("contracciones antes de término", "contracciones antes de termino"):
            datos_hemorragicos.append("contracciones antes de término")

        datos_hemorragicos = list(dict.fromkeys(datos_hemorragicos))
        rutas.append({
            "Ruta": "Hemorrágica",
            "Nivel": "Alta",
            "Datos activadores": ", ".join(datos_hemorragicos),
            "Acción educativa": "Valorar cantidad de sangrado, dolor, signos vitales, tono uterino y activar valoración obstétrica."
        })
        datos.extend([
            "sangrado vaginal",
            "riesgo de sangrado",
            "signos de alarma obstétrica",
            "riesgo de alteración de la díada materno-fetal"
        ])

    # =========================
    # RUTA DOLOR OBSTÉTRICO / SIGNO DE ALARMA
    # Dolor sin sangrado no debe contaminar como hemorragia.
    # =========================
    datos_dolor = []
    if dolor_abdominal or tiene("dolor abdominal", "dolor uterino"):
        datos_dolor.append("dolor abdominal/uterino")
    if (contracciones and semanas_gestacion < 37) or tiene("contracciones antes de término", "contracciones antes de termino"):
        datos_dolor.append("contracciones antes de término")

    if datos_dolor and not sangrado_real:
        datos_dolor = list(dict.fromkeys(datos_dolor))
        rutas.append({
            "Ruta": "Dolor obstétrico / signo de alarma",
            "Nivel": "Alta",
            "Datos activadores": ", ".join(datos_dolor),
            "Acción educativa": "Valorar intensidad del dolor, dinámica uterina, signos vitales, edad gestacional y descartar sangrado o urgencia obstétrica según protocolo."
        })
        datos.extend([
            "dolor abdominal",
            "dolor abdominal intenso",
            "dolor agudo",
            "signos de alarma obstétrica",
            "riesgo de alteración de la díada materno-fetal"
        ])

    # =========================
    # RUTA BIENESTAR FETAL
    # =========================
    datos_fetales = []
    if movimientos_fetales in ["Disminuidos", "Ausentes"]:
        datos_fetales.append(f"movimientos fetales {movimientos_fetales.lower()}")
    if tiene("disminución de movimientos fetales", "disminucion de movimientos fetales", "movimientos fetales disminuidos", "movimientos fetales ausentes"):
        datos_fetales.append("movimientos fetales alterados")

    if datos_fetales:
        datos_fetales = list(dict.fromkeys(datos_fetales))
        rutas.append({
            "Ruta": "Bienestar fetal",
            "Nivel": "Alta",
            "Datos activadores": ", ".join(datos_fetales),
            "Acción educativa": "Registrar movimientos fetales referidos y solicitar valoración de bienestar fetal según protocolo."
        })
        datos.extend([
            "disminución de movimientos fetales",
            "vigilancia fetal",
            "estado fetal anteparto",
            "riesgo de alteración de la díada materno-fetal"
        ])

    if not rutas:
        return [], "Sin ruta obstétrica crítica activada con los datos ingresados."

    resumen = []
    for ruta in rutas:
        resumen.append(
            f"[{ruta['Nivel']}] {ruta['Ruta']}: {ruta['Datos activadores']}. "
            f"Acción educativa: {ruta['Acción educativa']}"
        )

    datos = list(dict.fromkeys(datos))
    return datos, "\n".join(resumen)


def generar_resumen_clinico(df_resultados, puntaje_braden, riesgo_braden, eva_dolor, interpretacion_eva, glasgow_total, interpretacion_glasgow, puntaje_caidas, riesgo_caidas, spo2, interpretacion_spo2, fr, interpretacion_fr, hallazgos):
    if df_resultados.empty:
        return "No se encontraron diagnósticos suficientes. Se requiere valoración clínica completa."

    principales = df_resultados[df_resultados["Jerarquía"] == "Principal"]["NANDA"].tolist()
    complementarios = df_resultados[df_resultados["Jerarquía"] == "Complementario"]["NANDA"].tolist()

    lineas = []

    if principales:
        lineas.append("Prioridad principal: " + ", ".join(principales) + ".")

    if complementarios:
        lineas.append("Diagnósticos complementarios a vigilar: " + ", ".join(complementarios) + ".")

    lineas.append(f"Escala de Braden: {puntaje_braden} puntos, interpretación: {riesgo_braden}.")
    lineas.append(f"EVA del dolor: {eva_dolor}/10, interpretación: {interpretacion_eva}.")
    lineas.append(f"Glasgow: {glasgow_total}/15, interpretación: {interpretacion_glasgow}.")
    lineas.append(f"Riesgo de caídas: {puntaje_caidas} puntos, interpretación: {riesgo_caidas}.")
    lineas.append(f"Respiratorio: SpO₂ {spo2}%, {interpretacion_spo2}; FR {fr} rpm, {interpretacion_fr}.")

    if "embarazo" in hallazgos or "paciente obstétrica" in hallazgos:
        lineas.append("Obstétrico: vigilar presión arterial, cefalea, fosfenos, acúfenos, edema, sangrado, salida de líquido, fiebre, dolor abdominal y movimientos fetales según protocolo.")

    if "Deterioro del intercambio gaseoso" in principales or "Deterioro del intercambio gaseoso" in complementarios:
        lineas.append("Enfoque sugerido: valorar SpO₂, frecuencia respiratoria, coloración, disnea, uso de músculos accesorios y respuesta a oxígeno según indicación/protocolo.")

    if "Patrón respiratorio ineficaz" in principales or "Patrón respiratorio ineficaz" in complementarios:
        lineas.append("Enfoque sugerido: vigilar trabajo respiratorio, simetría torácica, tiraje, aleteo nasal, postura, fatiga y permeabilidad de vías aéreas.")

    if "Dolor agudo" in principales or "Dolor agudo" in complementarios:
        lineas.append("Enfoque sugerido: valorar localización, intensidad, duración, factores agravantes/aliviantes y respuesta a medidas analgésicas prescritas.")

    if "Riesgo de aspiración" in principales or "Riesgo de aspiración" in complementarios:
        lineas.append("Enfoque sugerido: vigilar nivel de conciencia, reflejo tusígeno, deglución, posición segura y datos de aspiración según protocolo.")

    if "Riesgo de caídas" in principales or "Riesgo de caídas" in complementarios:
        lineas.append("Enfoque sugerido: implementar medidas de seguridad, barandales según protocolo, acompañamiento, valoración del entorno y educación al cuidador.")

    if "Confusión aguda" in principales or "Confusión aguda" in complementarios:
        lineas.append("Enfoque sugerido: valorar orientación, cambios del estado mental, estímulos ambientales, seguridad y comunicación terapéutica.")

    if "Deterioro de la integridad cutánea" in principales or "Deterioro de la integridad cutánea" in complementarios:
        lineas.append("Enfoque sugerido: vigilancia de piel, prevención de lesiones por presión, control de humedad y cuidado de heridas.")

    if "Riesgo de infección" in principales or "Riesgo de infección" in complementarios:
        lineas.append("Enfoque sugerido: higiene de manos, técnica aséptica, vigilancia de exudado, fiebre, cambios locales y educación preventiva.")

    if "Deterioro de la movilidad física" in principales or "Deterioro de la movilidad física" in complementarios:
        lineas.append("Enfoque sugerido: movilización segura, cambios de posición, apoyo en transferencias y prevención de complicaciones por inmovilidad.")

    if "Déficit de autocuidado baño higiene" in principales or "Déficit de autocuidado baño higiene" in complementarios:
        lineas.append("Enfoque sugerido: apoyo parcial o total en higiene, conservación de dignidad, seguridad y educación al cuidador.")

    if "Desequilibrio nutricional inferior a las necesidades corporales" in principales or "Desequilibrio nutricional inferior a las necesidades corporales" in complementarios:
        lineas.append("Enfoque sugerido: valorar ingesta, peso, tolerancia, necesidades nutricionales y referencia según protocolo.")

    return "\n".join(lineas)



def generar_alertas_clinicas(
    spo2,
    fr,
    eva_dolor,
    puntaje_braden,
    glasgow_total,
    puntaje_caidas,
    riesgo_caidas,
    hallazgos_seleccionados
):
    alertas = []

    if spo2 <= 90:
        alertas.append({
            "Nivel": "Alta",
            "Área": "Respiratorio",
            "Alerta": f"SpO₂ {spo2}%: saturación críticamente baja.",
            "Acción sugerida": "Valorar dificultad respiratoria, coloración, trabajo respiratorio y notificar según protocolo institucional."
        })
    elif spo2 <= 93:
        alertas.append({
            "Nivel": "Media",
            "Área": "Respiratorio",
            "Alerta": f"SpO₂ {spo2}%: saturación baja.",
            "Acción sugerida": "Vigilar tendencia, síntomas respiratorios y respuesta a intervenciones indicadas."
        })

    if fr > 30:
        alertas.append({
            "Nivel": "Alta",
            "Área": "Respiratorio",
            "Alerta": f"FR {fr} rpm: taquipnea marcada.",
            "Acción sugerida": "Valorar trabajo respiratorio, fatiga, uso de músculos accesorios y signos de deterioro."
        })
    elif fr > 20:
        alertas.append({
            "Nivel": "Media",
            "Área": "Respiratorio",
            "Alerta": f"FR {fr} rpm: taquipnea.",
            "Acción sugerida": "Vigilar patrón respiratorio, disnea y evolución clínica."
        })

    if glasgow_total <= 8:
        alertas.append({
            "Nivel": "Alta",
            "Área": "Neurológico",
            "Alerta": f"Glasgow {glasgow_total}/15: compromiso neurológico grave.",
            "Acción sugerida": "Vigilar vía aérea, riesgo de aspiración, respuesta neurológica y actuar según protocolo."
        })
    elif glasgow_total <= 12:
        alertas.append({
            "Nivel": "Media",
            "Área": "Neurológico",
            "Alerta": f"Glasgow {glasgow_total}/15: compromiso neurológico moderado.",
            "Acción sugerida": "Realizar vigilancia neurológica seriada y medidas de seguridad."
        })

    if eva_dolor >= 7:
        alertas.append({
            "Nivel": "Media",
            "Área": "Dolor",
            "Alerta": f"EVA {eva_dolor}/10: dolor intenso.",
            "Acción sugerida": "Valorar características del dolor y respuesta a medidas indicadas."
        })

    if puntaje_braden <= 12:
        alertas.append({
            "Nivel": "Alta",
            "Área": "Piel y seguridad",
            "Alerta": f"Braden {puntaje_braden}: riesgo alto o muy alto de lesiones por presión.",
            "Acción sugerida": "Implementar prevención de lesiones por presión, cambios de posición y vigilancia de piel."
        })
    elif puntaje_braden <= 18:
        alertas.append({
            "Nivel": "Media",
            "Área": "Piel y seguridad",
            "Alerta": f"Braden {puntaje_braden}: riesgo de lesión por presión.",
            "Acción sugerida": "Reforzar inspección de piel, control de humedad y movilización."
        })

    if puntaje_caidas >= 6:
        alertas.append({
            "Nivel": "Alta",
            "Área": "Seguridad",
            "Alerta": f"Riesgo de caídas alto ({puntaje_caidas} puntos).",
            "Acción sugerida": "Aplicar medidas preventivas de caídas y acompañamiento según protocolo."
        })
    elif puntaje_caidas >= 3:
        alertas.append({
            "Nivel": "Media",
            "Área": "Seguridad",
            "Alerta": f"Riesgo de caídas moderado ({puntaje_caidas} puntos).",
            "Acción sugerida": "Vigilar deambulación, entorno seguro y necesidad de apoyo."
        })

    if "fiebre" in hallazgos_seleccionados and "herida" in hallazgos_seleccionados:
        alertas.append({
            "Nivel": "Media",
            "Área": "Infección",
            "Alerta": "Fiebre asociada a herida registrada.",
            "Acción sugerida": "Vigilar signos locales y sistémicos de infección y reportar según protocolo."
        })

    return alertas


def alertas_a_texto(alertas):
    if not alertas:
        return "Sin alertas educativas críticas detectadas con los datos ingresados."

    lineas = []
    for alerta in alertas:
        lineas.append(
            f"[{alerta['Nivel']}] {alerta['Área']}: {alerta['Alerta']} "
            f"Acción sugerida: {alerta['Acción sugerida']}"
        )

    return "\n".join(lineas)



# =========================
# SIDEBAR — RESUMEN EN TIEMPO REAL
# =========================

with st.sidebar:
    st.success("KIKE-NNN v18.1 | Ajuste fino obstétrico")
    st.info("Rutas: hipertensiva, RPM/infección, dolor obstétrico, hemorrágica y bienestar fetal.")
    st.markdown("---")
    st.caption("⚕️ Herramienta educativa — no uso clínico directo")


# =========================
# PESTAÑAS
# =========================

tab_datos, tab_valoracion, tab_braden, tab_resultados = st.tabs([
    "1. Datos del paciente",
    "2. Valoración rápida",
    "3. Escalas clínicas",
    "4. Resultados y exportación"
])


with tab_datos:
    st.header("1. Datos del paciente")

    col1, col2 = st.columns(2)

    with col1:
        tipo_paciente = st.selectbox(
            "Tipo de paciente",
            ["Adulto", "Geriátrico", "Pediátrico", "Obstétrico", "Recién nacido"]
        )
        st.info(recomendaciones_por_tipo(tipo_paciente))
        edad = st.number_input("Edad", min_value=0, max_value=120)
        sexo = st.selectbox("Sexo", ["Masculino", "Femenino", "No especificado"])
        dx_medico = st.text_input("Diagnóstico médico")

    with col2:
        signos_vitales = st.text_area("Signos vitales")
        factores_riesgo = st.text_area("Factores de riesgo")


with tab_valoracion:
    st.header("2. Valoración estructurada rápida")

    st.caption(
        "Selecciona los hallazgos presentes. Estos datos alimentan el motor NANDA junto con el texto libre."
    )

    col_resp, col_piel = st.columns(2)

    with col_resp:
        st.subheader("Respiratorio")
        disnea = st.checkbox("Disnea")
        cianosis = st.checkbox("Cianosis")
        hipoxia = st.checkbox("Hipoxia")
        saturacion_baja = st.checkbox("Saturación baja")
        taquipnea = st.checkbox("Taquipnea")
        musculos_accesorios = st.checkbox("Uso de músculos accesorios")
        estertores = st.checkbox("Estertores")

    with col_piel:
        st.subheader("Piel y heridas")
        herida = st.checkbox("Herida")
        ulcera = st.checkbox("Úlcera")
        enrojecimiento = st.checkbox("Enrojecimiento")
        exudado = st.checkbox("Exudado")
        piel_danada = st.checkbox("Piel dañada")
        humedad = st.checkbox("Humedad")
        postracion = st.checkbox("Postración")

    col_hidra, col_mov = st.columns(2)

    with col_hidra:
        st.subheader("Hidratación")
        mucosas_secas = st.checkbox("Mucosas secas")
        sed = st.checkbox("Sed")
        oliguria = st.checkbox("Oliguria ⚠️ (incluye contexto obstétrico)")
        taquicardia = st.checkbox("Taquicardia")
        vomito = st.checkbox("Vómito")
        diarrea = st.checkbox("Diarrea")

    with col_mov:
        st.subheader("Movilidad y autocuidado")
        inmovilidad = st.checkbox("Inmovilidad")
        debilidad = st.checkbox("Debilidad")
        dificultad_caminar = st.checkbox("Dificultad para caminar")
        higiene_deficiente = st.checkbox("Higiene deficiente")
        dependencia_higiene = st.checkbox("Dependencia para higiene")
        dolor_movimiento = st.checkbox("Dolor al movimiento")

    col_dolor, col_psico = st.columns(2)

    with col_dolor:
        st.subheader("Dolor")
        dolor = st.checkbox("Dolor")
        ardor = st.checkbox("Ardor")
        punzada = st.checkbox("Punzada")
        dolor_al_defecar = st.checkbox("Dolor al defecar")

    with col_psico:
        st.subheader("Psicoemocional y sueño")
        preocupacion = st.checkbox("Preocupación")
        nerviosismo = st.checkbox("Nerviosismo")
        inquietud = st.checkbox("Inquietud")
        temor = st.checkbox("Temor")
        insomnio = st.checkbox("Insomnio")
        estres = st.checkbox("Estrés")

    col_elim, col_extra = st.columns(2)

    with col_elim:
        st.subheader("Eliminación y nutrición")
        estrenimiento = st.checkbox("Estreñimiento")
        distension_abdominal = st.checkbox("Distensión abdominal")
        evacuaciones_duras = st.checkbox("Evacuaciones duras")
        perdida_peso = st.checkbox("Pérdida de peso")
        anorexia = st.checkbox("Anorexia")
        ingesta_insuficiente = st.checkbox("Ingesta insuficiente")

    with col_extra:
        st.subheader("Condiciones asociadas")
        vih = st.checkbox("VIH")
        neumonia = st.checkbox("Neumonía")
        diabetes = st.checkbox("Diabetes")
        adulto_mayor = st.checkbox("Adulto mayor")
        postoperatorio = st.checkbox("Postoperatorio")
        hospitalizacion = st.checkbox("Hospitalización")

    sintomas = st.text_area("Síntomas, hallazgos y datos relevantes en texto libre")


with tab_braden:
    st.header("3. Escalas clínicas")
    st.info(f"Perfil seleccionado: {tipo_paciente}. {recomendaciones_por_tipo(tipo_paciente)}")
    st.subheader("Módulo respiratorio avanzado")
    respiratorio_valorado = st.toggle("✅ Incluir módulo respiratorio en la valoración", value=False,
                                       help="Activa esta escala solo si valoraste SpO₂ y FR en el paciente.")

    col_r1, col_r2, col_r3 = st.columns(3)

    with col_r1:
        spo2 = st.number_input("SpO₂ (%)", min_value=50, max_value=100, value=98, step=1,
                                disabled=not respiratorio_valorado)

    with col_r2:
        fr = st.number_input("Frecuencia respiratoria (rpm)", min_value=0, max_value=80, value=18, step=1,
                              disabled=not respiratorio_valorado)

    with col_r3:
        oxigeno_suplementario = st.selectbox("Oxígeno suplementario", ["No", "Sí", "No especificado"],
                                              disabled=not respiratorio_valorado)

    interpretacion_spo2 = interpretar_spo2(spo2)
    interpretacion_fr = interpretar_fr_por_tipo(fr, tipo_paciente)

    st.info(
        f"Respiratorio: SpO₂ {spo2}% | {interpretacion_spo2} | "
        f"FR {fr} rpm | {interpretacion_fr}"
    )
    st.caption("Interpretación educativa general. Ajustar a edad, patología, altitud, protocolo institucional y contexto clínico.")

    st.subheader("Riesgo de lesiones por presión")
    braden_valorado = st.toggle("✅ Incluir Braden en la valoración", value=False,
                                 help="Activa solo si aplicaste la escala Braden al paciente.")

    col_b1, col_b2 = st.columns(2)

    with col_b1:
        braden_sensorial = st.selectbox(
            "Percepción sensorial", [1, 2, 3, 4], index=3,
            format_func=lambda x: {1: "1 - Completamente limitada", 2: "2 - Muy limitada",
                                    3: "3 - Ligeramente limitada", 4: "4 - Sin limitación"}[x]
        )
        braden_humedad = st.selectbox(
            "Humedad", [1, 2, 3, 4], index=3,
            format_func=lambda x: {1: "1 - Constantemente húmeda", 2: "2 - Muy húmeda",
                                    3: "3 - Ocasionalmente húmeda", 4: "4 - Raramente húmeda"}[x]
        )
        braden_actividad = st.selectbox(
            "Actividad", [1, 2, 3, 4], index=3,
            format_func=lambda x: {1: "1 - En cama", 2: "2 - En silla",
                                    3: "3 - Camina ocasionalmente", 4: "4 - Camina frecuentemente"}[x]
        )

    with col_b2:
        braden_movilidad = st.selectbox(
            "Movilidad", [1, 2, 3, 4], index=3,
            format_func=lambda x: {1: "1 - Completamente inmóvil", 2: "2 - Muy limitada",
                                    3: "3 - Ligeramente limitada", 4: "4 - Sin limitaciones"}[x]
        )
        braden_nutricion = st.selectbox(
            "Nutrición", [1, 2, 3, 4], index=3,
            format_func=lambda x: {1: "1 - Muy pobre", 2: "2 - Probablemente inadecuada",
                                    3: "3 - Adecuada", 4: "4 - Excelente"}[x]
        )
        braden_friccion = st.selectbox(
            "Fricción y cizallamiento", [1, 2, 3], index=2,
            format_func=lambda x: {1: "1 - Problema", 2: "2 - Problema potencial",
                                    3: "3 - Sin problema aparente"}[x]
        )

    puntaje_braden = braden_sensorial + braden_humedad + braden_actividad + braden_movilidad + braden_nutricion + braden_friccion
    riesgo_braden = interpretar_braden(puntaje_braden)

    st.info(f"Puntaje Braden: {puntaje_braden} | Interpretación: {riesgo_braden}")
    st.markdown("""
**Guía rápida Braden:** 19-23 sin riesgo · 15-18 leve · 13-14 moderado · 10-12 alto · ≤9 muy alto
""")

    st.subheader("Escala Visual Analógica del Dolor — EVA")
    eva_valorado = st.toggle("✅ Incluir EVA en la valoración", value=False,
                              help="Activa solo si valoraste el dolor con EVA. EVA 0 sin activar = no valorado.")
    eva_dolor = st.slider("Intensidad del dolor", min_value=0, max_value=10, value=0, step=1,
                          disabled=not eva_valorado)
    interpretacion_eva = interpretar_eva(eva_dolor)
    st.info(f"EVA: {eva_dolor}/10 | {interpretacion_eva}")

    st.subheader("Escala de Glasgow — Estado neurológico")
    glasgow_valorado = st.toggle("✅ Incluir Glasgow en la valoración", value=False,
                                  help="Activa solo si evaluaste el estado neurológico con Glasgow.")
    col_g1, col_g2, col_g3 = st.columns(3)

    with col_g1:
        glasgow_ocular = st.selectbox(
            "Respuesta ocular", [1, 2, 3, 4], index=3,
            format_func=lambda x: {1: "1 - No abre", 2: "2 - Al dolor",
                                    3: "3 - A la voz", 4: "4 - Espontánea"}[x]
        )

    with col_g2:
        glasgow_verbal = st.selectbox(
            "Respuesta verbal", [1, 2, 3, 4, 5], index=4,
            format_func=lambda x: {1: "1 - Sin respuesta", 2: "2 - Sonidos incomprensibles",
                                    3: "3 - Palabras inapropiadas", 4: "4 - Confuso",
                                    5: "5 - Orientado"}[x]
        )

    with col_g3:
        glasgow_motora = st.selectbox(
            "Respuesta motora", [1, 2, 3, 4, 5, 6], index=5,
            format_func=lambda x: {1: "1 - Sin respuesta", 2: "2 - Extensión anormal",
                                    3: "3 - Flexión anormal", 4: "4 - Retira al dolor",
                                    5: "5 - Localiza dolor", 6: "6 - Obedece órdenes"}[x]
        )

    glasgow_total = glasgow_ocular + glasgow_verbal + glasgow_motora
    interpretacion_glasgow = interpretar_glasgow(glasgow_total)
    st.info(f"Glasgow: {glasgow_total}/15 | {interpretacion_glasgow}")
    st.markdown("**Guía Glasgow:** 13-15 leve/conservado · 9-12 moderado · ≤8 grave")

    st.subheader("Tamizaje educativo de riesgo de caídas")
    caidas_valorado = st.toggle("✅ Incluir tamizaje de caídas en la valoración", value=False,
                                 help="Activa solo si realizaste el tamizaje de caídas al paciente.")
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        caida_previa = st.checkbox("Caída previa reciente")
        marcha_alterada = st.checkbox("Marcha inestable o alterada")
        ayuda_deambulacion = st.checkbox("Requiere ayuda para deambular")
        mareo_vertigo = st.checkbox("Mareo o vértigo")

    with col_c2:
        deficit_visual = st.checkbox("Déficit visual")
        medicamentos_riesgo = st.checkbox("Sedantes / antihipertensivos / diuréticos u otros fármacos de riesgo")
        confusion_caidas = st.checkbox("Confusión o desorientación")
        hipotension_ortostatica = st.checkbox("Hipotensión ortostática o síncope")

    puntaje_caidas = (
        (2 if caida_previa else 0) + (2 if marcha_alterada else 0) +
        (1 if ayuda_deambulacion else 0) + (1 if mareo_vertigo else 0) +
        (1 if deficit_visual else 0) + (1 if medicamentos_riesgo else 0) +
        (2 if confusion_caidas else 0) + (2 if hipotension_ortostatica else 0) +
        (1 if glasgow_total < 15 else 0)
    )
    riesgo_caidas = interpretar_riesgo_caidas(puntaje_caidas)
    st.info(f"Riesgo de caídas: {puntaje_caidas} puntos | {riesgo_caidas}")
    st.markdown("**Guía caídas:** 0 sin riesgo · 1-2 bajo · 3-5 moderado · ≥6 alto")

    # =========================
    # MÓDULO OBSTÉTRICO
    # =========================
    st.subheader("Módulo obstétrico ajustado")

    if tipo_paciente == "Obstétrico":
        st.info("Tamizaje educativo para signos de alarma obstétrica. No sustituye triage obstétrico, NOM vigente ni protocolo institucional.")

        col_o1, col_o2, col_o3 = st.columns(3)

        with col_o1:
            semanas_gestacion = st.number_input("Semanas de gestación", min_value=0, max_value=42, value=20, step=1)
            pas = st.number_input("Presión sistólica (mmHg)", min_value=60, max_value=240, value=120, step=1)

        with col_o2:
            gestas = st.number_input("Gestas", min_value=0, max_value=20, value=1, step=1)
            pad = st.number_input("Presión diastólica (mmHg)", min_value=30, max_value=160, value=80, step=1)

        with col_o3:
            temperatura = st.number_input("Temperatura (°C)", min_value=34.0, max_value=42.0, value=36.5, step=0.1)
            movimientos_fetales = st.selectbox(
                "Movimientos fetales referidos",
                ["No aplica / no valorado", "Presentes", "Disminuidos", "Ausentes"]
            )

        interpretacion_pa_obstetrica = interpretar_pa_obstetrica(pas, pad, semanas_gestacion)
        st.info(f"PA obstétrica: {pas}/{pad} mmHg | {interpretacion_pa_obstetrica}")

        col_o4, col_o5 = st.columns(2)

        with col_o4:
            st.markdown("**Signos neurológicos / hipertensivos**")
            cefalea_intensa = st.checkbox("Cefalea intensa o persistente")
            fosfenos = st.checkbox("Fosfenos / lucecitas / visión borrosa")
            acufenos = st.checkbox("Acúfenos / zumbido de oídos")
            epigastralgia = st.checkbox("Dolor epigástrico o en barra")
            edema_cara_manos = st.checkbox("Edema de cara o manos")
            convulsiones = st.checkbox("Convulsiones")

        with col_o5:
            st.markdown("**Sangrado, líquido, dolor y otros datos**")
            sangrado_vaginal = st.checkbox("Sangrado vaginal")
            salida_liquido = st.checkbox("Salida de líquido transvaginal")
            liquido_fetido = st.checkbox("Líquido con mal olor")
            liquido_verdoso = st.checkbox("Líquido verdoso")
            dolor_abdominal_intenso = st.checkbox("Dolor abdominal intenso")
            contracciones_antes_termino = st.checkbox("Contracciones antes de término")
            disminucion_mov_fetales = st.checkbox("Disminución o ausencia de movimientos fetales")
            nausea_vomito_persistente = st.checkbox("Náusea/vómito persistente")
            disuria_obstetrica = st.checkbox("Dolor o molestia al orinar")

        st.caption("Datos de alarma: sangrado, salida de líquido, cefalea intensa, fosfenos, acúfenos, edema, dolor abdominal intenso, fiebre y disminución de movimientos fetales requieren valoración según protocolo.")

    else:
        semanas_gestacion = 0
        gestas = 0
        pas = 120
        pad = 80
        temperatura = 36.5
        movimientos_fetales = "No aplica / no valorado"
        interpretacion_pa_obstetrica = "No aplica: perfil no obstétrico"
        cefalea_intensa = False
        fosfenos = False
        acufenos = False
        epigastralgia = False
        edema_cara_manos = False
        convulsiones = False
        sangrado_vaginal = False
        salida_liquido = False
        liquido_fetido = False
        liquido_verdoso = False
        dolor_abdominal_intenso = False
        contracciones_antes_termino = False
        disminucion_mov_fetales = False
        nausea_vomito_persistente = False
        disuria_obstetrica = False


# =========================
# CONSTRUCCIÓN DE HALLAZGOS
# =========================

checkboxes_valoracion = {
    "disnea": disnea, "cianosis": cianosis, "hipoxia": hipoxia,
    "saturación baja": saturacion_baja, "taquipnea": taquipnea,
    "uso de músculos accesorios": musculos_accesorios, "estertores": estertores,
    "herida": herida, "úlcera": ulcera, "enrojecimiento": enrojecimiento,
    "exudado": exudado, "piel dañada": piel_danada, "humedad": humedad,
    "postración": postracion, "mucosas secas": mucosas_secas, "sed": sed,
    "oliguria": oliguria, "taquicardia": taquicardia, "vómito": vomito,
    "diarrea": diarrea, "inmovilidad": inmovilidad, "debilidad": debilidad,
    "dificultad para caminar": dificultad_caminar, "higiene deficiente": higiene_deficiente,
    "dependencia para higiene": dependencia_higiene, "dolor al movimiento": dolor_movimiento,
    "dolor": dolor, "ardor": ardor, "punzada": punzada, "dolor al defecar": dolor_al_defecar,
    "preocupación": preocupacion, "nerviosismo": nerviosismo, "inquietud": inquietud,
    "temor": temor, "insomnio": insomnio, "estrés": estres,
    "estreñimiento": estrenimiento, "distensión abdominal": distension_abdominal,
    "evacuaciones duras": evacuaciones_duras, "pérdida de peso": perdida_peso,
    "anorexia": anorexia, "ingesta insuficiente": ingesta_insuficiente,
    "VIH": vih, "neumonía": neumonia, "diabetes": diabetes,
    "adulto mayor": adulto_mayor, "postoperatorio": postoperatorio,
    "hospitalización": hospitalizacion,
}

hallazgos_seleccionados = [h for h, v in checkboxes_valoracion.items() if v]

# Hallazgos desde escalas
hallazgos_braden = []
if braden_valorado:
    if puntaje_braden <= 18:
        hallazgos_braden += ["riesgo de lesión por presión", "inmovilidad", "deterioro de la integridad cutánea"]
    if braden_humedad <= 2:
        hallazgos_braden += ["humedad", "piel dañada"]
    if braden_actividad <= 2:
        hallazgos_braden += ["inmovilidad", "postración"]
    if braden_movilidad <= 2:
        hallazgos_braden += ["inmovilidad", "dificultad para caminar"]
    if braden_nutricion <= 2:
        hallazgos_braden += ["ingesta insuficiente", "nutrición comprometida"]
    if braden_friccion <= 2:
        hallazgos_braden += ["fricción", "cizallamiento"]

hallazgos_eva = []
if eva_valorado:
    if eva_dolor >= 4:
        hallazgos_eva += ["dolor", "dolor agudo", "molestia"]
    if eva_dolor >= 7:
        hallazgos_eva += ["dolor intenso", "prioridad alta", "punzada"]

hallazgos_glasgow = []
if glasgow_valorado:
    if glasgow_total <= 14:
        hallazgos_glasgow += ["confusión", "alteración del estado mental", "riesgo de caídas"]
    if glasgow_total <= 12:
        hallazgos_glasgow += ["nivel de conciencia disminuido", "somnolencia", "deterioro neurológico", "dificultad para caminar"]
    if glasgow_total <= 8:
        hallazgos_glasgow += ["riesgo de aspiración", "disminución del reflejo tusígeno", "respuesta verbal alterada",
                               "respuesta motora alterada", "dependencia para higiene", "inmovilidad"]

hallazgos_respiratorios = []
if respiratorio_valorado:
    if spo2 <= 95:
        hallazgos_respiratorios.append("saturación baja")
    if spo2 <= 93:
        hallazgos_respiratorios += ["hipoxia", "deterioro del intercambio gaseoso"]
    if spo2 <= 90:
        hallazgos_respiratorios += ["cianosis", "oxigenación comprometida", "prioridad alta"]
    if fr > 20:
        hallazgos_respiratorios += ["taquipnea", "patrón respiratorio ineficaz"]
    if fr > 30:
        hallazgos_respiratorios += ["uso de músculos accesorios", "fatiga de músculos respiratorios"]
    if fr < 12:
        hallazgos_respiratorios += ["bradipnea", "alteración respiratoria"]
    if oxigeno_suplementario == "Sí" and spo2 <= 95:
        hallazgos_respiratorios += ["requiere oxígeno suplementario", "monitorización respiratoria"]

hallazgos_caidas = []
if puntaje_caidas >= 1:
    hallazgos_caidas.append("riesgo de caídas")
if puntaje_caidas >= 3:
    hallazgos_caidas += ["dificultad para caminar", "marcha inestable", "debilidad"]
if puntaje_caidas >= 6:
    hallazgos_caidas += ["alteración de la movilidad", "alteración del estado mental", "hospitalización"]
if caida_previa:
    hallazgos_caidas.append("caída previa")
if marcha_alterada:
    hallazgos_caidas.append("marcha inestable")
if ayuda_deambulacion:
    hallazgos_caidas.append("requiere ayuda para deambular")
if mareo_vertigo:
    hallazgos_caidas += ["mareo", "vértigo"]
if deficit_visual:
    hallazgos_caidas.append("déficit visual")
if medicamentos_riesgo:
    hallazgos_caidas.append("medicamentos de riesgo")
if confusion_caidas:
    hallazgos_caidas += ["confusión", "desorientación"]
if hipotension_ortostatica:
    hallazgos_caidas.append("hipotensión ortostática")

hallazgos_obstetricos = []
if tipo_paciente == "Obstétrico":
    hallazgos_obstetricos += ["embarazo", "paciente obstétrica", "vigilancia obstétrica"]
    if semanas_gestacion >= 20:
        hallazgos_obstetricos.append("embarazo mayor de 20 semanas")
    if pas >= 140 or pad >= 90:
        hallazgos_obstetricos += ["hipertensión", "preeclampsia", "riesgo de alteración de la díada materno-fetal"]
    if pas >= 160 or pad >= 110:
        hallazgos_obstetricos += ["hipertensión severa", "prioridad alta", "signos de alarma obstétrica"]
    if cefalea_intensa:
        hallazgos_obstetricos += ["cefalea intensa", "signos de alarma obstétrica", "ansiedad"]
    if fosfenos:
        hallazgos_obstetricos += ["fosfenos", "visión borrosa", "signos de alarma obstétrica"]
    if acufenos:
        hallazgos_obstetricos += ["acúfenos", "zumbido de oídos", "signos de alarma obstétrica"]
    if epigastralgia:
        hallazgos_obstetricos += ["epigastralgia", "dolor epigástrico", "dolor"]
    if edema_cara_manos:
        hallazgos_obstetricos += ["edema", "edema de cara", "edema de manos"]
    if convulsiones:
        hallazgos_obstetricos += ["convulsiones", "alteración neurológica", "prioridad alta"]
    if sangrado_vaginal:
        hallazgos_obstetricos += ["sangrado", "sangrado vaginal", "riesgo de sangrado", "dolor abdominal", "prioridad alta"]
    if salida_liquido:
        hallazgos_obstetricos += ["salida de líquido transvaginal", "ruptura de membranas", "riesgo de infección", "vigilancia obstétrica"]
    if liquido_fetido:
        hallazgos_obstetricos += ["líquido fétido", "fiebre", "infección", "riesgo de infección"]
    if liquido_verdoso:
        hallazgos_obstetricos += ["líquido verdoso", "riesgo de alteración de la díada materno-fetal", "prioridad alta"]
    if temperatura >= 38:
        hallazgos_obstetricos += ["fiebre", "temperatura elevada", "riesgo de infección"]
    if dolor_abdominal_intenso:
        hallazgos_obstetricos += ["dolor abdominal intenso", "dolor", "dolor agudo", "prioridad alta"]
    if contracciones_antes_termino:
        hallazgos_obstetricos += ["contracciones uterinas", "dolor de parto", "dolor", "amenaza de parto pretérmino"]
    if disminucion_mov_fetales or movimientos_fetales in ["Disminuidos", "Ausentes"]:
        hallazgos_obstetricos += ["disminución de movimientos fetales", "riesgo de alteración de la díada materno-fetal", "prioridad alta"]
    if nausea_vomito_persistente:
        hallazgos_obstetricos += ["náusea", "nauseas", "vómito", "mucosas secas", "déficit de volumen de líquidos"]
    if disuria_obstetrica:
        hallazgos_obstetricos += ["disuria", "dolor al orinar", "infección urinaria", "riesgo de infección"]

hallazgos_perfil = []
if tipo_paciente == "Geriátrico":
    hallazgos_perfil += ["adulto mayor", "riesgo de caídas", "fragilidad", "vigilancia de piel"]
elif tipo_paciente == "Obstétrico":
    hallazgos_perfil += ["embarazo", "vigilancia obstétrica", "signos de alarma obstétrica"]
elif tipo_paciente == "Recién nacido":
    hallazgos_perfil += ["recién nacido", "vigilancia neonatal", "termorregulación"]
elif tipo_paciente == "Pediátrico":
    hallazgos_perfil += ["paciente pediátrico", "vigilancia por edad", "educación al cuidador"]

# EVA ajuste v18.1
if tipo_paciente == "Obstétrico" and bool(dolor_abdominal_intenso) and int(eva_dolor) == 0:
    interpretacion_eva = "EVA no valorada o pendiente; dolor abdominal intenso registrado, se recomienda cuantificar dolor."

# Combinar hallazgos — FIXED: pa_sistolica/cefalea mismatches corregidos
hallazgos_obstetricos_ruta, resumen_rutas_obstetricas = evaluar_rutas_obstetricas(
    tipo_paciente=tipo_paciente,
    semanas_gestacion=semanas_gestacion,
    pa_sistolica=pas,                          # FIX v18.1: era pa_sistolica (siempre 0)
    pa_diastolica=pad,                          # FIX v18.1: era pa_diastolica (siempre 0)
    temperatura=temperatura,
    cefalea=cefalea_intensa,                    # FIX v18.1: usa nombre correcto del widget
    fosfenos=fosfenos,                          # FIX v18.1: era fosfenos_obstetricos (siempre False)
    acufenos=acufenos,                          # FIX v18.1: era acufenos_obstetricos (siempre False)
    epigastralgia=epigastralgia,               # FIX v18.1: era epigastralgia_obstetrica (siempre False)
    edema=edema_cara_manos,                    # FIX v18.1: era edema_obstetrico (siempre False)
    convulsiones=convulsiones,                  # FIX v18.1: era convulsiones_obstetricas (siempre False)
    sangrado=sangrado_vaginal,
    salida_liquido=salida_liquido,
    liquido_fetido=liquido_fetido,
    liquido_verdoso=liquido_verdoso,
    dolor_abdominal=dolor_abdominal_intenso,   # FIX v18.1: era dolor_abdominal_obstetrico (siempre False)
    contracciones=contracciones_antes_termino,  # FIX v18.1: era contracciones_pretermino (siempre False)
    movimientos_fetales=movimientos_fetales,
    hallazgos_detectados=hallazgos_seleccionados
)

# Seguro clínico: hipertensiva crítica solo si PA severa o convulsiones reales
try:
    pa_severa_obs = tipo_paciente == "Obstétrico" and int(semanas_gestacion) >= 20 and (int(pas) >= 160 or int(pad) >= 110)
except Exception:
    pa_severa_obs = False

conv_reales = bool(convulsiones) or any(
    str(h).lower().strip() in ["convulsiones", "convulsión", "eclampsia"]
    for h in hallazgos_seleccionados
)

if (tipo_paciente == "Obstétrico"
    and "[Crítica] Hipertensiva / preeclampsia" in resumen_rutas_obstetricas
    and not pa_severa_obs and not conv_reales):
    resumen_rutas_obstetricas = resumen_rutas_obstetricas.replace(
        "[Crítica] Hipertensiva / preeclampsia",
        "[Alta] Hipertensiva / preeclampsia"
    )

# Enriquecimiento obstétrico
if tipo_paciente == "Obstétrico":
    if "Hipertensiva / preeclampsia" in resumen_rutas_obstetricas:
        hallazgos_obstetricos_ruta += ["riesgo de alteración de la díada materno-fetal",
                                        "preeclampsia", "hipertensión", "signos de alarma obstétrica",
                                        "ansiedad", "preocupación"]
    if "RPM / infección" in resumen_rutas_obstetricas:
        hallazgos_obstetricos_ruta += ["riesgo de infección materno-fetal", "salida de líquido transvaginal",
                                        "ruptura de membranas", "riesgo de infección",
                                        "signos de alarma obstétrica", "riesgo de alteración de la díada materno-fetal"]
    if "Hemorrágica" in resumen_rutas_obstetricas:
        hallazgos_obstetricos_ruta += ["riesgo de sangrado", "sangrado vaginal", "dolor abdominal",
                                        "signos de alarma obstétrica", "riesgo de alteración de la díada materno-fetal"]
    if "Dolor obstétrico / signo de alarma" in resumen_rutas_obstetricas:
        hallazgos_obstetricos_ruta += ["dolor abdominal", "dolor abdominal intenso", "dolor agudo",
                                        "signos de alarma obstétrica", "riesgo de alteración de la díada materno-fetal"]
    if "Bienestar fetal" in resumen_rutas_obstetricas:
        hallazgos_obstetricos_ruta += ["disminución de movimientos fetales", "vigilancia fetal",
                                        "estado fetal anteparto", "riesgo de alteración de la díada materno-fetal",
                                        "signos de alarma obstétrica"]

# Combinar todo y deduplicar
hallazgos_seleccionados = list(dict.fromkeys(
    hallazgos_seleccionados
    + hallazgos_obstetricos
    + hallazgos_obstetricos_ruta
    + hallazgos_perfil
    + hallazgos_respiratorios
    + hallazgos_braden
    + hallazgos_eva
    + hallazgos_glasgow
    + hallazgos_caidas
))

# =========================
# SIDEBAR — STATS EN TIEMPO REAL
# =========================
with st.sidebar:
    st.markdown("---")
    n_hallazgos = len([h for h, v in checkboxes_valoracion.items() if v])
    n_alertas_prev = 0
    if spo2 <= 90 or fr > 30 or glasgow_total <= 8 or puntaje_braden <= 12 or puntaje_caidas >= 6:
        n_alertas_prev += 1
    if tipo_paciente == "Obstétrico" and (pas >= 140 or pad >= 90 or convulsiones or sangrado_vaginal):
        n_alertas_prev += 1

    st.markdown(f"**Perfil:** {tipo_paciente}")
    st.markdown(f"**Hallazgos activos:** {n_hallazgos}")
    if n_alertas_prev > 0:
        st.error(f"⚠️ Posibles alertas detectadas")
    else:
        st.success("Sin alertas críticas previas")
    st.markdown("---")
    st.caption("v18.1 | Leininger · Xalapa, Ver.")


# =========================
# TAB 4 — RESULTADOS Y EXPORTACIÓN
# =========================

with tab_resultados:
    st.header("4. Resultados y exportación")

    # Preview obstétrico — siempre visible si aplica
    if tipo_paciente == "Obstétrico" and resumen_rutas_obstetricas not in ["Sin ruta obstétrica crítica activada con los datos ingresados.", "No aplica"]:
        st.subheader("🔴 Ruta obstétrica activa")
        st.warning(resumen_rutas_obstetricas)

    # Instrucciones si no se ha generado nada aún
    if "plan_generado" not in st.session_state:
        st.info(
            "✅ Completa los datos en las pestañas 1, 2 y 3, luego presiona **Generar Plan de Cuidados** "
            "para obtener diagnósticos NANDA con vinculación NOC/NIC, alertas clínicas y exportación."
        )
        col_hint1, col_hint2, col_hint3 = st.columns(3)
        with col_hint1:
            st.markdown("**Tab 1** — Datos del paciente, Dx médico")
        with col_hint2:
            st.markdown("**Tab 2** — Hallazgos y síntomas")
        with col_hint3:
            st.markdown("**Tab 3** — Escalas (Braden, EVA, Glasgow...)")

    if st.button("🩺 Generar Plan de Cuidados", type="primary"):
        with st.spinner("Analizando hallazgos y generando plan educativo..."):
            texto_estructurado = " ".join(hallazgos_seleccionados)
            texto_clinico = f"{tipo_paciente} {dx_medico} {signos_vitales} {factores_riesgo} {sintomas} {texto_estructurado}"

            datos_paciente = {
                "Tipo de paciente": tipo_paciente,
                "Edad": edad,
                "Sexo": sexo,
                "Diagnóstico médico": dx_medico,
                "Signos vitales": signos_vitales,
                "Factores de riesgo": factores_riesgo,
                "SpO2 (%)": spo2 if respiratorio_valorado else "No valorado",
                "Interpretación SpO2": interpretacion_spo2 if respiratorio_valorado else "No valorado",
                "Frecuencia respiratoria (rpm)": fr if respiratorio_valorado else "No valorado",
                "Interpretación FR": interpretacion_fr if respiratorio_valorado else "No valorado",
                "Oxígeno suplementario": oxigeno_suplementario if respiratorio_valorado else "No valorado",
                "Puntaje Braden": puntaje_braden if braden_valorado else "No valorado",
                "Interpretación Braden": riesgo_braden if braden_valorado else "No valorado",
                "EVA dolor": eva_dolor if eva_valorado else "No valorado",
                "Interpretación EVA": interpretacion_eva if eva_valorado else "No valorado",
                "Glasgow total": glasgow_total if glasgow_valorado else "No valorado",
                "Interpretación Glasgow": interpretacion_glasgow if glasgow_valorado else "No valorado",
                "Puntaje riesgo de caídas": puntaje_caidas if caidas_valorado else "No valorado",
                "Interpretación riesgo de caídas": riesgo_caidas if caidas_valorado else "No valorado",
                "Semanas de gestación": semanas_gestacion if tipo_paciente == "Obstétrico" else "No aplica",
                "Gestas": gestas if tipo_paciente == "Obstétrico" else "No aplica",
                "PA obstétrica (mmHg)": f"{pas}/{pad}" if tipo_paciente == "Obstétrico" else "No aplica",
                "Interpretación PA obstétrica": interpretacion_pa_obstetrica,
                "Temperatura (°C)": temperatura if tipo_paciente == "Obstétrico" else "No aplica",
                "Movimientos fetales": movimientos_fetales if tipo_paciente == "Obstétrico" else "No aplica",
                "Ruta obstétrica activada": resumen_rutas_obstetricas if tipo_paciente == "Obstétrico" else "No aplica",
                "Hallazgos estructurados": ", ".join(hallazgos_seleccionados),
                "Datos clínicos texto libre": sintomas,
            }

            # Valores efectivos: solo entra al motor de alertas si la escala fue valorada
            _spo2_ef = spo2 if respiratorio_valorado else 98
            _fr_ef = fr if respiratorio_valorado else 18
            _eva_ef = eva_dolor if eva_valorado else 0
            _braden_ef = puntaje_braden if braden_valorado else 23
            _glasgow_ef = glasgow_total if glasgow_valorado else 15
            _caidas_ef = puntaje_caidas if caidas_valorado else 0
            _rcaidas_ef = riesgo_caidas if caidas_valorado else "No valorado"

            # Alertas clínicas generales
            alertas_clinicas = generar_alertas_clinicas(
                spo2=_spo2_ef, fr=_fr_ef, eva_dolor=_eva_ef,
                puntaje_braden=_braden_ef, glasgow_total=_glasgow_ef,
                puntaje_caidas=_caidas_ef, riesgo_caidas=_rcaidas_ef,
                hallazgos_seleccionados=hallazgos_seleccionados
            )

            # Alerta EVA v18.1
            if tipo_paciente == "Obstétrico" and bool(dolor_abdominal_intenso) and int(eva_dolor) == 0:
                alertas_clinicas.append({
                    "Nivel": "Media", "Área": "Dolor / EVA",
                    "Alerta": "Dolor abdominal intenso registrado, EVA en 0 o no capturada.",
                    "Acción sugerida": "Cuantificar dolor con EVA u otra escala institucional."
                })

            # Alertas obstétricas
            alertas_obstetricas = generar_alertas_obstetricas(
                tipo_paciente=tipo_paciente, semanas_gestacion=semanas_gestacion,
                pas=pas, pad=pad, temperatura=temperatura,
                cefalea_intensa=cefalea_intensa, fosfenos=fosfenos, acufenos=acufenos,
                epigastralgia=epigastralgia, edema_cara_manos=edema_cara_manos,
                convulsiones=convulsiones, sangrado_vaginal=sangrado_vaginal,
                salida_liquido=salida_liquido, liquido_fetido=liquido_fetido,
                liquido_verdoso=liquido_verdoso, dolor_abdominal_intenso=dolor_abdominal_intenso,
                contracciones_antes_termino=contracciones_antes_termino,
                disminucion_mov_fetales=disminucion_mov_fetales,
                nausea_vomito_persistente=nausea_vomito_persistente,
                disuria_obstetrica=disuria_obstetrica,
            )
            alertas_clinicas.extend(alertas_obstetricas)
            datos_paciente["Alertas clínicas educativas"] = alertas_a_texto(alertas_clinicas)

            # Buscar diagnósticos
            df_resultados = buscar_diagnosticos(texto_clinico)
            df_resultados = enriquecer_plan(df_resultados)

        # Persistimos todo en session_state: sin esto, cualquier interacción
        # posterior (escribir una justificación, mover un toggle) reinicia
        # st.button a False y todo este resultado desaparecía de pantalla.
        st.session_state.plan_generado = True
        st.session_state.df_resultados = df_resultados
        st.session_state.datos_paciente = datos_paciente
        st.session_state.alertas_clinicas = alertas_clinicas
        # Nuevo plan generado: limpiamos justificaciones de un caso anterior
        st.session_state.justificaciones = {}

    if st.session_state.get("plan_generado"):
        df_resultados = st.session_state.df_resultados
        datos_paciente = st.session_state.datos_paciente
        alertas_clinicas = st.session_state.alertas_clinicas

        # Valores efectivos recalculados (cambian si el estudiante ajusta una
        # escala después de generar el plan, sin tener que volver a generarlo)
        _spo2_ef = spo2 if respiratorio_valorado else 98
        _fr_ef = fr if respiratorio_valorado else 18
        _eva_ef = eva_dolor if eva_valorado else 0
        _braden_ef = puntaje_braden if braden_valorado else 23
        _glasgow_ef = glasgow_total if glasgow_valorado else 15
        _caidas_ef = puntaje_caidas if caidas_valorado else 0
        _rcaidas_ef = riesgo_caidas if caidas_valorado else "No valorado"

        # =========================
        # MÉTRICAS RÁPIDAS
        # =========================
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Hallazgos activos", len([h for h, v in checkboxes_valoracion.items() if v]))
        with m2:
            st.metric("Alertas clínicas", len(alertas_clinicas), delta=None)
        with m3:
            n_dx = len(df_resultados) if not df_resultados.empty else 0
            st.metric("Diagnósticos sugeridos", n_dx)
        with m4:
            n_princ = len(df_resultados[df_resultados["Jerarquía"] == "Principal"]) if not df_resultados.empty else 0
            st.metric("Dx principales", n_princ)

        st.markdown("---")

        # =========================
        # ALERTAS CLÍNICAS
        # =========================
        st.subheader("⚠️ Alertas clínicas educativas")
        if alertas_clinicas:
            alertas_altas = [a for a in alertas_clinicas if a["Nivel"] == "Alta"]
            alertas_medias = [a for a in alertas_clinicas if a["Nivel"] != "Alta"]
            for alerta in alertas_altas:
                st.error(f"**[ALTA] {alerta['Área']}** — {alerta['Alerta']}  \n_{alerta['Acción sugerida']}_")
            for alerta in alertas_medias:
                st.warning(f"**[MEDIA] {alerta['Área']}** — {alerta['Alerta']}  \n_{alerta['Acción sugerida']}_")
        else:
            st.success("Sin alertas educativas críticas detectadas con los datos ingresados.")

        st.markdown("---")

        # =========================
        # DIAGNÓSTICOS
        # =========================
        if df_resultados.empty:
            st.warning("No se encontraron coincidencias suficientes. Agrega más hallazgos clínicos o texto libre para ampliar la búsqueda.")
        else:
            st.subheader("📋 Resumen clínico educativo")
            resumen_clinico = generar_resumen_clinico(
                df_resultados,
                _braden_ef, riesgo_braden if braden_valorado else "No valorado",
                _eva_ef, interpretacion_eva if eva_valorado else "No valorado",
                _glasgow_ef, interpretacion_glasgow if glasgow_valorado else "No valorado",
                _caidas_ef, _rcaidas_ef,
                _spo2_ef, interpretacion_spo2 if respiratorio_valorado else "No valorado",
                _fr_ef, interpretacion_fr if respiratorio_valorado else "No valorado",
                hallazgos_seleccionados
            )
            st.info(resumen_clinico)
            datos_paciente["Resumen clínico educativo"] = resumen_clinico

            dx_principales = df_resultados[df_resultados["Jerarquía"] == "Principal"]
            dx_complementarios = df_resultados[df_resultados["Jerarquía"] == "Complementario"]

            col_dxa, col_dxb = st.columns(2)
            with col_dxa:
                st.subheader("🔵 Diagnósticos principales")
                if dx_principales.empty:
                    st.info("Sin diagnósticos principales con puntaje alto.")
                else:
                    cols_tabla = ["Código", "NANDA", "Puntaje", "Confianza", "Prioridad"]
                    st.dataframe(dx_principales[cols_tabla], use_container_width=True, hide_index=True)

            with col_dxb:
                st.subheader("⚪ Diagnósticos complementarios")
                if dx_complementarios.empty:
                    st.info("Sin diagnósticos complementarios.")
                else:
                    cols_tabla = ["Código", "NANDA", "Puntaje", "Confianza", "Prioridad"]
                    st.dataframe(dx_complementarios[cols_tabla], use_container_width=True, hide_index=True)

            st.markdown("---")

            # =========================
            # 🎓 RAZONAMIENTO CLÍNICO — MÓDULO DE JUSTIFICACIÓN
            # =========================
            st.subheader("🎓 Razonamiento clínico — acepta o rechaza cada diagnóstico")
            st.caption(
                "Por cada diagnóstico sugerido decide si lo aceptas o lo rechazas para "
                "este caso y argumenta tu decisión. Esto es lo que se evalúa: no el "
                "diagnóstico en sí, sino el razonamiento detrás de tu decisión."
            )

            if "justificaciones" not in st.session_state:
                st.session_state.justificaciones = {}

            for _, fila in df_resultados.iterrows():
                nanda_nombre = fila["NANDA"]
                codigo_dx = fila["Código"]
                criterios_dx = nanda_criterios.get(codigo_dx, [])
                key_base = f"justif_{codigo_dx}"

                with st.expander(f"🧩 {nanda_nombre} — {fila['Confianza']} ({fila['Jerarquía']})"):
                    decision = st.radio(
                        "¿Aceptas este diagnóstico para este caso?",
                        ["Sin decidir", "Aceptado", "Rechazado"],
                        key=f"{key_base}_decision",
                        horizontal=True
                    )

                    if criterios_dx:
                        criterios_sel = st.multiselect(
                            "Criterios clínicos que sostienen tu decisión "
                            "(características definitorias / factores relacionados)",
                            options=criterios_dx,
                            key=f"{key_base}_criterios"
                        )
                    else:
                        criterios_sel = []
                        st.caption("Este diagnóstico no tiene criterios catalogados; argumenta solo en el texto libre.")

                    texto_justif = st.text_area(
                        "Justificación clínica, en tus propias palabras",
                        key=f"{key_base}_texto",
                        placeholder="Explica por qué aceptas o rechazas este diagnóstico con base en los datos de este caso..."
                    )

                    st.session_state.justificaciones[nanda_nombre] = {
                        "decision": decision,
                        "confianza": fila["Confianza"],
                        "jerarquia": fila["Jerarquía"],
                        "puntaje": fila["Puntaje"],
                        "criterios": criterios_sel,
                        "justificacion": texto_justif,
                    }

            justificaciones_actuales = st.session_state.justificaciones
            n_aceptados = len([v for v in justificaciones_actuales.values() if v["decision"] == "Aceptado"])
            n_rechazados = len([v for v in justificaciones_actuales.values() if v["decision"] == "Rechazado"])
            n_pendientes = len(df_resultados) - n_aceptados - n_rechazados
            if n_pendientes > 0:
                st.warning(f"Te faltan {n_pendientes} diagnóstico(s) por decidir y argumentar antes de exportar el caso completo.")
            else:
                st.success(f"Decidiste y argumentaste los {len(df_resultados)} diagnósticos: {n_aceptados} aceptado(s), {n_rechazados} rechazado(s).")

            st.markdown("---")

            # =========================
            # EXPORTACIÓN
            # =========================
            st.subheader("📥 Exportar plan de cuidados")
            excel_file = generar_excel(df_resultados, datos_paciente, justificaciones_actuales)
            word_file = generar_word(df_resultados, datos_paciente, justificaciones_actuales)

            col_xl, col_wd = st.columns(2)
            with col_xl:
                st.download_button(
                    label="📊 Descargar Excel",
                    data=excel_file,
                    file_name="plan_cuidados_nnn_v19.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            with col_wd:
                st.download_button(
                    label="📄 Descargar Word",
                    data=word_file,
                    file_name="plan_cuidados_nnn_v19.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )

            st.markdown("---")

            # =========================
            # PLAN NARRATIVO — EXPANDIBLE
            # =========================
            st.subheader("📖 Plan narrativo NANDA-NOC-NIC")
            st.caption("Haz clic en cada diagnóstico para expandir su plan completo.")

            for _, fila in df_resultados.iterrows():
                nivel_badge = "🔵" if fila["Jerarquía"] == "Principal" else "⚪"
                with st.expander(f"{nivel_badge} {fila['NANDA']} — Puntaje {fila['Puntaje']} | {fila['Confianza']}"):
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.markdown(f"**Código:** {fila['Código']}")
                        st.markdown(f"**Dominio:** {fila['Dominio']}")
                        st.markdown(f"**Clase:** {fila['Clase']}")
                        st.markdown(f"**Jerarquía:** {fila['Jerarquía']}")
                        st.markdown(f"**Prioridad:** {fila['Prioridad']}")
                    with col_info2:
                        st.markdown(f"**NOC sugerido:** {fila['NOC sugerido']}")
                        st.markdown(f"**NIC sugerido:** {fila['NIC sugerido']}")
                        st.markdown(f"**Meta esperada:** {fila['Meta esperada']}")
                    st.markdown(f"**Definición:** {fila['Definición']}")
                    st.markdown(f"**Coincidencias clínicas:** {fila['Coincidencias']}")
                    st.markdown("**Indicadores NOC:**")
                    st.code(fila["Indicadores NOC"], language=None)
                    st.markdown("**Actividades NIC:**")
                    st.code(fila["Actividades NIC"], language=None)
                    if fila["Fundamentos"]:
                        st.markdown("**Fundamentos:**")
                        st.info(fila["Fundamentos"])
                    st.caption(f"⚠️ {fila['Nota']}")

    st.markdown("---")
    st.caption("KIKE-NNN v19 | Uso educativo exclusivo | Escuela de Enfermería y Obstetricia Leininger · Xalapa, Veracruz | No certificado por COFEPRIS")
