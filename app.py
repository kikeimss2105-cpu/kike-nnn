import streamlit as st
import pandas as pd
from utils.exportadores import generar_excel, generar_word

from engine.carga import cargar_catalogos
from engine.criterios import construir_criterios_nanda
from engine.motor import buscar_diagnosticos
from engine.plan import enriquecer_plan
from engine.interpretaciones import (
    interpretar_braden, interpretar_eva, interpretar_glasgow,
    interpretar_riesgo_caidas, interpretar_spo2, interpretar_fr_adulto,
    interpretar_fr_por_tipo, recomendaciones_por_tipo, interpretar_pa_obstetrica,
)
from engine.obstetrico import generar_alertas_obstetricas, evaluar_rutas_obstetricas
from engine.resumen import generar_resumen_clinico, generar_alertas_clinicas, alertas_a_texto

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

    st.image("https://img.shields.io/badge/KIKE--NNN-v19-blue?style=flat-square", width=160)
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


# =========================
# CARGA DE BASES CSV
# =========================

# =========================
# CARGA DE BASES CSV (engine/carga.py)
# =========================

@st.cache_data
def cargar_datos():
    cat = cargar_catalogos(data_dir="data")
    return cat.nanda, cat.enlaces, cat.noc_indicadores, cat.nic_actividades, cat.fundamentos, cat.metas


nanda_df, enlaces_df, noc_indicadores_df, nic_actividades_df, fundamentos_df, metas_df = cargar_datos()


@st.cache_data
def _construir_criterios_nanda_cacheado(nanda_df):
    return construir_criterios_nanda(nanda_df)


nanda_criterios = _construir_criterios_nanda_cacheado(nanda_df)


# =========================
# MOTOR DE PUNTUACIÓN
# =========================


# =========================
# SIDEBAR — RESUMEN EN TIEMPO REAL
# =========================

with st.sidebar:
    st.success("KIKE-NNN v19 | Justificación clínica + 60 dx NANDA")
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
    st.caption("v19 | Leininger · Xalapa, Ver.")


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
            df_resultados = buscar_diagnosticos(texto_clinico, nanda_df, enlaces_df)
            df_resultados = enriquecer_plan(df_resultados, metas_df, noc_indicadores_df, nic_actividades_df, fundamentos_df)

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
