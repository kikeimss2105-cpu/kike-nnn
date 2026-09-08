import streamlit as st
import pandas as pd
from uuid import uuid4
from utils.exportadores import generar_excel, generar_word, generar_word_docente
from engine.docente import analizar_sesion

from engine.carga import cargar_catalogos
from engine.criterios import construir_criterios_nanda
from engine.motor import buscar_diagnosticos
from engine.plan import enriquecer_plan
from engine.evidencia import (
    ElegibilidadEvidencia,
    EstadoValidacion,
    FuenteEvidencia,
    NaturalezaEvidencia,
    evidencia_estructurada,
    evidencias_desde_eva,
    evidencias_desde_hallazgos,
)
from engine.parser_negaciones import conceptos_catalogo, etiquetas_nanda, parsear_texto_libre
from engine.interpretaciones import (
    interpretar_braden, interpretar_eva,
    interpretar_riesgo_caidas, interpretar_spo2,
    recomendaciones_por_tipo, interpretar_pa_obstetrica,
)
from engine.obstetrico import (
    clasificar_datos_rpm,
    evaluar_rutas_obstetricas,
    extraer_hallazgos_obstetricos,
    generar_alertas_obstetricas,
)
from engine.resumen import generar_resumen_clinico, generar_alertas_clinicas, alertas_a_texto
from engine.gordon import cargar_patrones_gordon, hallazgos_desde_respuestas
from engine.texto import consolidar_hallazgos
from engine.respiratorio import evaluar_fr, evidencias_desde_resultado_fr, evidencias_desde_spo2
from engine.glasgow import (
    OPCIONES_MOTORA,
    OPCIONES_OCULAR,
    OPCIONES_VERBAL,
    actualizar_datos_paciente_glasgow,
    evaluar_glasgow,
    resolver_id_valoracion,
    sincronizar_alertas_glasgow,
)
from engine.neonatal import (
    calcular_apgar,
    calcular_capurro_a,
    calcular_capurro_b,
    calcular_silverman,
    serializar_resultado,
)

st.set_page_config(page_title="KIKE-NNN | Apoyo al razonamiento clínico", layout="wide")


# =========================
# ESTILO VISUAL (rediseño 2026-09-01) — solo CSS/HTML, sin tocar logica clinica
# =========================
def _inyectar_estilo():
    st.markdown("""
    <style>
      html, body, [data-testid="stAppViewContainer"] {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }

      /* Chips de estado (Valorado / Sin valorar) */
      .knn-chip {
        display: inline-flex; align-items: center; gap: 6px;
        font-size: 0.72rem; font-weight: 700; padding: 3px 10px;
        border-radius: 999px; margin: 2px 0 12px;
      }
      .knn-chip::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
      .knn-chip.on  { color: #1b7a4c; background: #e6f4ec; }
      .knn-chip.off { color: #5c7a82; background: #eef4f4; }

      /* Resultado numerico destacado (Glasgow, Braden, EVA, caidas) */
      .knn-resultado {
        font-family: ui-monospace, "SFMono-Regular", Consolas, monospace; font-weight: 700;
      }

      /* Botones: el primario (Generar Plan) pesa mas que los secundarios (exportar) */
      button[kind="primary"] {
        font-weight: 700 !important; box-shadow: 0 4px 14px -4px rgba(0,100,120,0.45) !important;
      }
      button[kind="secondary"] { font-weight: 600 !important; }

      /* Alertas: franja de color mas visible por severidad, ademas del fondo nativo */
      div[data-testid="stAlert"] { border-radius: 10px !important; }

      /* Separacion mas clara entre subsecciones de escalas */
      h3 { margin-top: 0.4rem !important; }
    </style>
    """, unsafe_allow_html=True)


def _chip(valorado: bool) -> str:
    if valorado:
        return "<span class='knn-chip on'>Valorado</span>"
    return "<span class='knn-chip off'>Sin valorar</span>"


_inyectar_estilo()


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

    st.image("https://img.shields.io/badge/KIKE--NNN-v1.0.0--rc1-blue?style=flat-square", width=180)
    st.markdown("## ⚕️ Aviso de uso obligatorio")

    st.markdown("""
<div class="disclaimer-box">

**KIKE-NNN es una herramienta exclusivamente educativa de apoyo al razonamiento clínico en enfermería.**

Antes de continuar, lee y acepta los siguientes términos:

- **No emite diagnósticos de enfermería definitivos** ni diagnósticos médicos de ningún tipo.
- **No sustituye** el juicio clínico del profesional o estudiante de enfermería.
- **No reemplaza** protocolos institucionales vigentes (GPC-IMSS, ACOG, NOM, guías locales).
- Las rutas clínicas generadas (hipertensiva, RPM, valoración de sangrado obstétrico, etc.) son **guías educativas orientativas**, no órdenes clínicas.
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


@st.cache_data
def _cargar_patrones_gordon_cacheado():
    return cargar_patrones_gordon(data_dir="data")


patrones_gordon = _cargar_patrones_gordon_cacheado()


# =========================
# MOTOR DE PUNTUACIÓN
# =========================


# =========================
# SIDEBAR — RESUMEN EN TIEMPO REAL
# =========================

with st.sidebar:
    st.success("KIKE-NNN v1.0.0-rc1 | Candidato técnico educativo")
    st.info("Rutas: hipertensiva, RPM/infección, dolor obstétrico, valoración de sangrado y bienestar fetal.")
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

    with st.expander("🧭 Valoración por Patrones Funcionales de Gordon (piloto — 4 de 11 patrones)"):
        st.caption(
            "Módulo en construcción: organiza la valoración según los Patrones Funcionales de "
            "Gordon. Los hallazgos marcados aquí se suman a los del resto del formulario — no lo "
            "reemplazan. Actualmente cubre 4 de 11 patrones; los demás requieren definir el "
            "criterio clínico de sus preguntas."
        )
        respuestas_gordon = {}
        for patron in patrones_gordon:
            if patron.estado != "listo":
                continue
            st.markdown(f"**{patron.nombre}**")
            cols_gordon = st.columns(3)
            for i, item in enumerate(patron.items):
                with cols_gordon[i % 3]:
                    respuestas_gordon[item.item_id] = st.checkbox(
                        item.pregunta, key=f"gordon_{item.item_id}"
                    )
        hallazgos_gordon = hallazgos_desde_respuestas(patrones_gordon, respuestas_gordon)

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

    resultado_apgar = None
    resultado_silverman = None
    resultado_capurro = None

    if tipo_paciente == "Recién nacido":
        with st.expander("👶 Escalas neonatales deterministas", expanded=True):
            st.caption(
                "Selecciona 'No valorado' cuando el componente no fue observado. "
                "El engine no calcula escalas incompletas ni sustituye datos faltantes por cero."
            )

            st.markdown("**APGAR**")
            opciones_basicas = [None, 0, 1, 2]
            columnas_apgar = st.columns(5)
            etiquetas_apgar = ("Apariencia", "Pulso", "Gesticulación", "Actividad", "Respiración")
            valores_apgar = [
                columna.selectbox(
                    etiqueta,
                    opciones_basicas,
                    format_func=lambda valor: "No valorado" if valor is None else str(valor),
                    key=f"neo_apgar_{indice}",
                )
                for indice, (columna, etiqueta) in enumerate(zip(columnas_apgar, etiquetas_apgar))
            ]
            resultado_apgar = calcular_apgar(*valores_apgar)
            if resultado_apgar.calculado:
                st.info(f"APGAR: {resultado_apgar.total}/10 · {resultado_apgar.interpretacion}")
                st.json(dict(resultado_apgar.desglose))
            else:
                st.warning("APGAR no calculado. Faltan: " + ", ".join(resultado_apgar.datos_faltantes))

            st.markdown("**Silverman-Andersen**")
            columnas_silverman = st.columns(5)
            etiquetas_silverman = (
                "Movimiento toracoabdominal", "Tiraje intercostal", "Retracción xifoidea",
                "Aleteo nasal", "Quejido espiratorio",
            )
            valores_silverman = [
                columna.selectbox(
                    etiqueta,
                    opciones_basicas,
                    format_func=lambda valor: "No valorado" if valor is None else str(valor),
                    key=f"neo_silverman_{indice}",
                )
                for indice, (columna, etiqueta) in enumerate(zip(columnas_silverman, etiquetas_silverman))
            ]
            resultado_silverman = calcular_silverman(*valores_silverman)
            if resultado_silverman.calculado:
                st.info(
                    f"Silverman-Andersen: {resultado_silverman.total}/10 · "
                    f"{resultado_silverman.interpretacion}"
                )
                st.json(dict(resultado_silverman.desglose))
            else:
                st.warning(
                    "Silverman-Andersen no calculado. Faltan: "
                    + ", ".join(resultado_silverman.datos_faltantes)
                )

            st.markdown("**Capurro A/B**")
            variante_capurro = st.radio("Variante", ("A", "B"), horizontal=True)
            opciones_capurro = {
                "forma_oreja": [None, 0, 8, 16, 24],
                "tamano_glandula_mamaria": [None, 0, 5, 10, 15],
                "textura_piel": [None, 0, 5, 10, 15, 20],
                "pliegues_plantares": [None, 0, 5, 10, 15, 20],
            }
            if variante_capurro == "B":
                opciones_capurro["formacion_pezon"] = [None, 0, 5, 10, 15]
            valores_capurro = {}
            for nombre, opciones in opciones_capurro.items():
                valores_capurro[nombre] = st.selectbox(
                    nombre.replace("_", " ").capitalize(),
                    opciones,
                    format_func=lambda valor: "No valorado" if valor is None else str(valor),
                    key=f"neo_capurro_{nombre}",
                )
            if variante_capurro == "A":
                signo_bufanda = st.selectbox(
                    "Signo de la bufanda", [None, 0, 6, 12, 18], key="neo_bufanda",
                    format_func=lambda valor: "No valorado" if valor is None else str(valor),
                )
                caida_cabeza = st.selectbox(
                    "Caída de la cabeza", [None, 0, 4, 8, 12], key="neo_cabeza",
                    format_func=lambda valor: "No valorado" if valor is None else str(valor),
                )
                resultado_capurro = calcular_capurro_a(
                    **valores_capurro,
                    signo_bufanda=signo_bufanda,
                    caida_cabeza=caida_cabeza,
                )
            else:
                resultado_capurro = calcular_capurro_b(**valores_capurro)
            if resultado_capurro.calculado:
                st.info(
                    f"Capurro {variante_capurro}: {resultado_capurro.semanas_completas} semanas "
                    f"y {resultado_capurro.dias_adicionales} días · {resultado_capurro.formula}"
                )
                st.json(dict(resultado_capurro.desglose))
            else:
                st.warning("Capurro no calculado. Faltan: " + ", ".join(resultado_capurro.datos_faltantes))

    st.divider()
    st.subheader("🫁 Módulo respiratorio avanzado")
    respiratorio_valorado = st.toggle("✅ Incluir módulo respiratorio en la valoración", value=False,
                                       help="Activa esta escala solo si valoraste SpO₂ y FR en el paciente.")
    st.markdown(_chip(respiratorio_valorado), unsafe_allow_html=True)

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

    resultado_fr = evaluar_fr(
        fr if respiratorio_valorado else None,
        valorado=respiratorio_valorado,
        perfil=tipo_paciente,
        edad=edad,
        contexto_obstetrico={"aplica": tipo_paciente == "Obstétrico"},
        origen="respiratorio.fr",
        id_dato_primario="fr_capturada",
    )
    if respiratorio_valorado:
        interpretacion_spo2 = interpretar_spo2(spo2)
        interpretacion_fr = resultado_fr.interpretacion
        st.info(
            f"Respiratorio: SpO₂ {spo2}% | {interpretacion_spo2} | "
            f"FR {resultado_fr.valor_rpm} rpm | {interpretacion_fr}"
        )
    else:
        interpretacion_spo2 = "No valorado"
        interpretacion_fr = "No valorado"
        st.info("Módulo respiratorio no valorado.")
    evidencias_spo2_clinicas = evidencias_desde_spo2(
        spo2 if respiratorio_valorado else None,
        valorado=respiratorio_valorado,
        id_dato_primario="spo2_capturada",
    )
    st.caption("Interpretación educativa general. Ajustar a edad, patología, altitud, protocolo institucional y contexto clínico.")

    st.divider()
    st.subheader("🩹 Riesgo de lesiones por presión — Braden")
    braden_valorado = st.toggle("✅ Incluir Braden en la valoración", value=False,
                                 help="Activa solo si aplicaste la escala Braden al paciente.")
    st.markdown(_chip(braden_valorado), unsafe_allow_html=True)

    col_b1, col_b2 = st.columns(2)

    with col_b1:
        braden_sensorial = st.selectbox(
            "Percepción sensorial", [1, 2, 3, 4], index=3,
            format_func=lambda x: {1: "1 - Completamente limitada", 2: "2 - Muy limitada",
                                    3: "3 - Ligeramente limitada", 4: "4 - Sin limitación"}[x], disabled=not braden_valorado
        )
        braden_humedad = st.selectbox(
            "Humedad", [1, 2, 3, 4], index=3,
            format_func=lambda x: {1: "1 - Constantemente húmeda", 2: "2 - Muy húmeda",
                                    3: "3 - Ocasionalmente húmeda", 4: "4 - Raramente húmeda"}[x], disabled=not braden_valorado
        )
        braden_actividad = st.selectbox(
            "Actividad", [1, 2, 3, 4], index=3,
            format_func=lambda x: {1: "1 - En cama", 2: "2 - En silla",
                                    3: "3 - Camina ocasionalmente", 4: "4 - Camina frecuentemente"}[x], disabled=not braden_valorado
        )

    with col_b2:
        braden_movilidad = st.selectbox(
            "Movilidad", [1, 2, 3, 4], index=3,
            format_func=lambda x: {1: "1 - Completamente inmóvil", 2: "2 - Muy limitada",
                                    3: "3 - Ligeramente limitada", 4: "4 - Sin limitaciones"}[x], disabled=not braden_valorado
        )
        braden_nutricion = st.selectbox(
            "Nutrición", [1, 2, 3, 4], index=3,
            format_func=lambda x: {1: "1 - Muy pobre", 2: "2 - Probablemente inadecuada",
                                    3: "3 - Adecuada", 4: "4 - Excelente"}[x], disabled=not braden_valorado
        )
        braden_friccion = st.selectbox(
            "Fricción y cizallamiento", [1, 2, 3], index=2,
            format_func=lambda x: {1: "1 - Problema", 2: "2 - Problema potencial",
                                    3: "3 - Sin problema aparente"}[x], disabled=not braden_valorado
        )

    puntaje_braden = braden_sensorial + braden_humedad + braden_actividad + braden_movilidad + braden_nutricion + braden_friccion
    riesgo_braden = interpretar_braden(puntaje_braden) if braden_valorado else "No valorado"

    if braden_valorado:
        st.info(f"Puntaje Braden: {puntaje_braden} | Interpretación: {riesgo_braden}")
    else:
        st.info("Braden: No valorado")
    st.markdown("""
**Guía rápida Braden:** 19-23 sin riesgo · 15-18 leve · 13-14 moderado · 10-12 alto · ≤9 muy alto
""")

    st.divider()
    st.subheader("📈 Escala Visual Analógica del Dolor — EVA")
    eva_valorado = st.toggle("✅ Incluir EVA en la valoración", value=False,
                              help="Activa solo si valoraste el dolor con EVA. EVA 0 sin activar = no valorado.")
    st.markdown(_chip(eva_valorado), unsafe_allow_html=True)
    eva_dolor = st.slider("Intensidad del dolor", min_value=0, max_value=10, value=0, step=1,
                          disabled=not eva_valorado)
    interpretacion_eva = interpretar_eva(eva_dolor) if eva_valorado else "No valorado"
    if eva_valorado:
        st.info(f"EVA: {eva_dolor}/10 | {interpretacion_eva}")
    else:
        st.info("EVA: No valorado")
    evidencias_eva_clinicas = evidencias_desde_eva(
        eva_dolor if eva_valorado else None,
        valorado=eva_valorado,
        id_dato_primario="eva_dolor",
    )

    st.divider()
    st.subheader("🧠 Escala de Glasgow — Estado neurológico")
    glasgow_valorado = st.toggle("✅ Incluir Glasgow en la valoración", value=False,
                                  help="Activa solo si evaluaste el estado neurológico con Glasgow.")
    st.markdown(_chip(glasgow_valorado), unsafe_allow_html=True)
    col_g1, col_g2, col_g3 = st.columns(3)

    with col_g1:
        glasgow_ocular = st.selectbox(
            "Respuesta ocular", [1, 2, 3, 4], index=3,
            format_func=lambda x: f"{x} - {OPCIONES_OCULAR[x]}",
            disabled=not glasgow_valorado,
        )

    with col_g2:
        glasgow_verbal = st.selectbox(
            "Respuesta verbal", [1, 2, 3, 4, 5], index=4,
            format_func=lambda x: f"{x} - {OPCIONES_VERBAL[x]}",
            disabled=not glasgow_valorado,
        )

    with col_g3:
        glasgow_motora = st.selectbox(
            "Respuesta motora", [1, 2, 3, 4, 5, 6], index=5,
            format_func=lambda x: f"{x} - {OPCIONES_MOTORA[x]}",
            disabled=not glasgow_valorado,
        )

    glasgow_valorado_previo = st.session_state.get("glasgow_valorado_previo", False)
    st.session_state.glasgow_id_valoracion = resolver_id_valoracion(
        valorado_actual=glasgow_valorado,
        valorado_previo=glasgow_valorado_previo,
        id_actual=st.session_state.get("glasgow_id_valoracion"),
    )
    st.session_state.glasgow_valorado_previo = glasgow_valorado
    resultado_glasgow = evaluar_glasgow(
        glasgow_ocular,
        glasgow_verbal,
        glasgow_motora,
        valorado=glasgow_valorado,
        id_valoracion=st.session_state.get("glasgow_id_valoracion"),
    )
    glasgow_total = resultado_glasgow.total
    interpretacion_glasgow = resultado_glasgow.interpretacion
    if resultado_glasgow.valorado:
        st.info(f"Glasgow: {glasgow_total}/15 | {interpretacion_glasgow}")
    else:
        st.info("Glasgow: No valorado")
    st.markdown("**Guía Glasgow:** 13-15 leve/conservado · 9-12 moderado · ≤8 grave")

    st.divider()
    st.subheader("🚶 Tamizaje educativo de riesgo de caídas")
    caidas_valorado = st.toggle("✅ Incluir tamizaje de caídas en la valoración", value=False,
                                 help="Activa solo si realizaste el tamizaje de caídas al paciente.")
    st.markdown(_chip(caidas_valorado), unsafe_allow_html=True)
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        caida_previa = st.checkbox("Caída previa reciente", disabled=not caidas_valorado)
        marcha_alterada = st.checkbox("Marcha inestable o alterada", disabled=not caidas_valorado)
        ayuda_deambulacion = st.checkbox("Requiere ayuda para deambular", disabled=not caidas_valorado)
        mareo_vertigo = st.checkbox("Mareo o vértigo", disabled=not caidas_valorado)

    with col_c2:
        deficit_visual = st.checkbox("Déficit visual", disabled=not caidas_valorado)
        medicamentos_riesgo = st.checkbox("Sedantes / antihipertensivos / diuréticos u otros fármacos de riesgo", disabled=not caidas_valorado)
        confusion_caidas = st.checkbox("Confusión o desorientación", disabled=not caidas_valorado)
        hipotension_ortostatica = st.checkbox("Hipotensión ortostática o síncope", disabled=not caidas_valorado)

    puntaje_caidas = (
        (2 if caida_previa else 0) + (2 if marcha_alterada else 0) +
        (1 if ayuda_deambulacion else 0) + (1 if mareo_vertigo else 0) +
        (1 if deficit_visual else 0) + (1 if medicamentos_riesgo else 0) +
        (2 if confusion_caidas else 0) + (2 if hipotension_ortostatica else 0)
    )
    riesgo_caidas = interpretar_riesgo_caidas(puntaje_caidas) if caidas_valorado else "No valorado"
    if caidas_valorado:
        st.info(f"Riesgo de caídas: {puntaje_caidas} puntos | {riesgo_caidas}")
    else:
        st.info("Riesgo de caídas: No valorado")
    st.markdown("**Guía caídas:** 0 sin riesgo · 1-2 bajo · 3-5 moderado · ≥6 alto")

    # =========================
    # MÓDULO OBSTÉTRICO
    # =========================
    st.subheader("Módulo obstétrico ajustado")

    if tipo_paciente == "Obstétrico":
        st.info("Tamizaje educativo para signos de alarma obstétrica. No sustituye triage obstétrico, NOM vigente ni protocolo institucional.")

        col_o1, col_o2, col_o3 = st.columns(3)

        with col_o1:
            semanas_gestacion = st.number_input("Semanas de gestación", min_value=1, max_value=42, value=None, step=1, placeholder="No valorado")
            st.caption("Registro en semanas enteras; los días gestacionales no se modelan en esta fase.")
            pas = st.number_input("Presión sistólica (mmHg)", min_value=60, max_value=240, value=None, step=1, placeholder="No valorada")

        with col_o2:
            gestas = st.number_input("Gestas", min_value=0, max_value=20, value=1, step=1)
            pad = st.number_input("Presión diastólica (mmHg)", min_value=30, max_value=160, value=None, step=1, placeholder="No valorada")

        with col_o3:
            temperatura = st.number_input("Temperatura (°C)", min_value=34.0, max_value=42.0, value=None, step=0.1, placeholder="No valorada")
            movimientos_fetales = st.selectbox(
                "Movimientos fetales referidos",
                ["No valorado", "Presentes", "Disminuidos", "Ausentes"]
            )

        interpretacion_pa_obstetrica = interpretar_pa_obstetrica(pas, pad, semanas_gestacion)
        pas_texto = "No valorada" if pas is None else str(pas)
        pad_texto = "No valorada" if pad is None else str(pad)
        st.info(f"PA obstétrica: {pas_texto}/{pad_texto} mmHg | {interpretacion_pa_obstetrica}")

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
            contracciones_antes_termino = st.checkbox("Contracciones uterinas")
            nausea_vomito_persistente = st.checkbox("Náusea/vómito persistente")
            disuria_obstetrica = st.checkbox("Dolor o molestia al orinar")

        st.caption("Datos que requieren valoración según contexto y protocolo: sangrado, salida de líquido, cefalea intensa, fosfenos, acúfenos, edema, dolor abdominal intenso, fiebre y movimientos fetales referidos como disminuidos o ausentes.")

    else:
        semanas_gestacion = None
        gestas = 0
        pas = None
        pad = None
        temperatura = None
        movimientos_fetales = "No valorado"
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

hallazgos_eva = [
    evidencia.concepto for evidencia in evidencias_eva_clinicas
    if evidencia.concepto != "escala visual analógica del dolor"
]

hallazgos_respiratorios = []
if respiratorio_valorado:
    hallazgos_respiratorios.extend(
        evidencia.concepto for evidencia in evidencias_spo2_clinicas
        if evidencia.derivada_de is not None
    )
    hallazgos_respiratorios.extend(resultado_fr.terminos_derivados)
    if oxigeno_suplementario == "Sí":
        hallazgos_respiratorios.append("requiere oxígeno suplementario")

hallazgos_caidas = []
if caidas_valorado:
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

hallazgos_obstetricos = extraer_hallazgos_obstetricos(
    tipo_paciente=tipo_paciente,
    semanas_gestacion=semanas_gestacion,
    pas=pas,
    pad=pad,
    temperatura=temperatura,
    cefalea_intensa=cefalea_intensa,
    fosfenos=fosfenos,
    acufenos=acufenos,
    epigastralgia=epigastralgia,
    edema_cara_manos=edema_cara_manos,
    convulsiones=convulsiones,
    sangrado_vaginal=sangrado_vaginal,
    salida_liquido=salida_liquido,
    liquido_fetido=liquido_fetido,
    liquido_verdoso=liquido_verdoso,
    dolor_abdominal_intenso=dolor_abdominal_intenso,
    contracciones_antes_termino=contracciones_antes_termino,
    movimientos_fetales=movimientos_fetales,
    nausea_vomito_persistente=nausea_vomito_persistente,
    disuria_obstetrica=disuria_obstetrica,
)

categorias_rpm = clasificar_datos_rpm(
    salida_liquido=salida_liquido,
    liquido_fetido=liquido_fetido,
    liquido_verdoso=liquido_verdoso,
    temperatura=temperatura,
)

# El motor NANDA recibe los datos RPM observados, no las sospechas ni las
# inferencias pedagógicas creadas por la ruta.
terminos_rpm_clasificados = {
    termino
    for categoria in categorias_rpm.values()
    for termino in categoria
}
hallazgos_obstetricos_para_nanda = [
    hallazgo for hallazgo in hallazgos_obstetricos
    if hallazgo not in terminos_rpm_clasificados
]
hallazgos_obstetricos_para_nanda.extend(categorias_rpm["DATOS_OBSERVADOS"])

hallazgos_perfil = []
if tipo_paciente == "Geriátrico":
    hallazgos_perfil += ["adulto mayor", "riesgo de caídas", "fragilidad", "vigilancia de piel"]
elif tipo_paciente == "Obstétrico":
    hallazgos_perfil += ["embarazo", "vigilancia obstétrica"]
elif tipo_paciente == "Recién nacido":
    hallazgos_perfil += ["recién nacido", "vigilancia neonatal", "termorregulación"]
elif tipo_paciente == "Pediátrico":
    hallazgos_perfil += ["paciente pediátrico", "vigilancia por edad", "educación al cuidador"]

# EVA ajuste v18.1
if tipo_paciente == "Obstétrico" and bool(dolor_abdominal_intenso) and (not eva_valorado or int(eva_dolor) == 0):
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

# Combinar todo y deduplicar
hallazgos_seleccionados = consolidar_hallazgos(
    hallazgos_seleccionados, hallazgos_obstetricos_para_nanda,
    hallazgos_perfil, hallazgos_respiratorios, hallazgos_braden, hallazgos_eva,
    hallazgos_caidas, hallazgos_gordon,
)

# =========================
# SIDEBAR — STATS EN TIEMPO REAL
# =========================
with st.sidebar:
    st.markdown("---")
    n_hallazgos = len([h for h, v in checkboxes_valoracion.items() if v])
    n_alertas_prev = 0
    alerta_fr_alta = resultado_fr.alerta is not None and resultado_fr.alerta.nivel == "Alta"
    if ((respiratorio_valorado and spo2 <= 90) or alerta_fr_alta
            or (glasgow_total is not None and glasgow_total <= 8)
            or (braden_valorado and puntaje_braden <= 12)
            or (caidas_valorado and puntaje_caidas >= 6)):
        n_alertas_prev += 1
    pa_obstetrica_elevada = (
        (pas is not None and pas >= 140)
        or (pad is not None and pad >= 90)
    )
    if tipo_paciente == "Obstétrico" and (pa_obstetrica_elevada or convulsiones or sangrado_vaginal):
        n_alertas_prev += 1

    st.markdown(f"**Perfil:** {tipo_paciente}")
    st.markdown(f"**Hallazgos activos:** {n_hallazgos}")
    if n_alertas_prev > 0:
        st.warning("Situaciones obstétricas que requieren valoración")
    else:
        st.success("Sin situaciones obstétricas adicionales que requieran valoración")
    st.markdown("---")
    st.caption("v1.0.0-rc1 | Leininger · Xalapa, Ver.")


# =========================
# TAB 4 — RESULTADOS Y EXPORTACIÓN
# =========================

# Entradas de la valoración que originó el plan, independientes de navegación
# y justificaciones. Se construyen de nuevo en cada ejecución, sin alias a
# widgets ni a los diccionarios de resultados almacenados.
valoracion_actual = {
    "perfil": (tipo_paciente, edad, sexo),
    "texto": (dx_medico, signos_vitales, factores_riesgo, sintomas),
    "hallazgos": dict(checkboxes_valoracion),
    "gordon": dict(respuestas_gordon),
    "respiratorio": (
        respiratorio_valorado,
        (spo2, fr, oxigeno_suplementario) if respiratorio_valorado else None,
    ),
    "braden": (
        braden_valorado,
        (braden_sensorial, braden_humedad, braden_actividad, braden_movilidad,
         braden_nutricion, braden_friccion) if braden_valorado else None,
    ),
    "eva": (eva_valorado, eva_dolor if eva_valorado else None),
    "glasgow": resultado_glasgow,
    "caidas": (
        caidas_valorado,
        (caida_previa, marcha_alterada, ayuda_deambulacion, mareo_vertigo,
         deficit_visual, medicamentos_riesgo, confusion_caidas,
         hipotension_ortostatica) if caidas_valorado else None,
    ),
    "obstetrico": (
        semanas_gestacion, gestas, pas, pad, temperatura, movimientos_fetales,
        cefalea_intensa, fosfenos, acufenos, epigastralgia, edema_cara_manos,
        convulsiones, sangrado_vaginal, salida_liquido, liquido_fetido,
        liquido_verdoso, dolor_abdominal_intenso, contracciones_antes_termino,
        nausea_vomito_persistente, disuria_obstetrica,
    ) if tipo_paciente == "Obstétrico" else None,
    "neonatal": (
        serializar_resultado(resultado_apgar),
        serializar_resultado(resultado_silverman),
        serializar_resultado(resultado_capurro),
    ) if tipo_paciente == "Recién nacido" else None,
}

if (
    st.session_state.get("plan_generado")
    and st.session_state.get("valoracion_generada") != valoracion_actual
):
    st.session_state.plan_generado = False
    st.session_state.resultados_invalidados = True
    for clave in ("df_resultados", "datos_paciente", "alertas_clinicas", "valoracion_generada"):
        st.session_state.pop(clave, None)

with tab_resultados:
    st.header("4. Resultados y exportación")

    # Preview obstétrico — siempre visible si aplica
    if tipo_paciente == "Obstétrico" and resumen_rutas_obstetricas not in ["Sin ruta obstétrica crítica activada con los datos ingresados.", "No aplica"]:
        st.subheader("Ruta educativa obstétrica activa")
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

            vocabulario_clinico = conceptos_catalogo(nanda_df)
            conclusiones_nanda = etiquetas_nanda(nanda_df)
            evidencias_clinicas = []
            estados_parsing = []
            for origen_texto, valor_texto in (
                ("diagnostico_medico", dx_medico),
                ("signos_vitales_texto", signos_vitales),
                ("factores_riesgo_texto", factores_riesgo),
                ("sintomas_texto_libre", sintomas),
            ):
                resultado_parsing = parsear_texto_libre(
                    valor_texto,
                    vocabulario_clinico,
                    origen=origen_texto,
                    conclusiones_diagnosticas=conclusiones_nanda,
                )
                evidencias_clinicas.extend(resultado_parsing.evidencias)
                estados_parsing.append(resultado_parsing.estado)

            evidencias_clinicas.extend(evidencias_desde_hallazgos(
                [h for h, v in checkboxes_valoracion.items() if v],
                fuente=FuenteEvidencia.OBSERVADO,
                origen="valoracion_rapida",
                naturaleza=NaturalezaEvidencia.DATO_PRIMARIO_OBSERVADO,
                estado_validacion=EstadoValidacion.VALIDADO,
                elegibilidad=ElegibilidadEvidencia.PUNTUABLE,
            ))
            evidencias_clinicas.extend(evidencias_desde_hallazgos(
                hallazgos_gordon,
                fuente=FuenteEvidencia.REFERIDO_ESTRUCTURADO,
                origen="gordon",
                naturaleza=NaturalezaEvidencia.DATO_PRIMARIO_REFERIDO,
                estado_validacion=EstadoValidacion.VALIDADO,
                elegibilidad=ElegibilidadEvidencia.PUNTUABLE,
            ))
            evidencias_clinicas.extend(evidencias_eva_clinicas)
            evidencias_clinicas.extend(evidencias_desde_resultado_fr(resultado_fr))
            evidencias_clinicas.extend(evidencias_spo2_clinicas)
            if respiratorio_valorado and oxigeno_suplementario == "Sí":
                evidencias_clinicas.append(evidencia_estructurada(
                    "requiere oxígeno suplementario",
                    fuente=FuenteEvidencia.REFERIDO_ESTRUCTURADO,
                    origen="respiratorio.oxigeno_suplementario",
                    id_dato_primario="oxigeno_suplementario",
                    naturaleza=NaturalezaEvidencia.DATO_PRIMARIO_REFERIDO,
                    estado_validacion=EstadoValidacion.VALIDADO,
                    elegibilidad=ElegibilidadEvidencia.PUNTUABLE,
                ))
            for origen_escala, hallazgos_escala in (
                ("braden", hallazgos_braden),
                ("caidas", hallazgos_caidas),
            ):
                evidencias_clinicas.extend(evidencias_desde_hallazgos(
                    hallazgos_escala,
                    fuente=FuenteEvidencia.INFERIDO,
                    origen=origen_escala,
                    derivada_de=f"escala_{origen_escala}",
                ))
            evidencias_clinicas.extend(evidencias_desde_hallazgos(
                hallazgos_obstetricos_para_nanda,
                fuente=FuenteEvidencia.GENERADO_SISTEMA,
                origen="valoracion_obstetrica",
                derivada_de="datos_obstetricos_estructurados",
            ))
            evidencias_clinicas.extend(evidencias_desde_hallazgos(
                hallazgos_perfil,
                fuente=FuenteEvidencia.INFERIDO,
                origen="perfil_paciente",
                derivada_de="tipo_paciente",
                naturaleza=NaturalezaEvidencia.CONTEXTO,
                estado_validacion=EstadoValidacion.VALIDADO,
                elegibilidad=ElegibilidadEvidencia.NO_PUNTUABLE,
            ))

            datos_paciente = {
                "Tipo de paciente": tipo_paciente,
                "Edad": edad,
                "Sexo": sexo,
                "Diagnóstico médico": dx_medico,
                "Signos vitales": signos_vitales,
                "Factores de riesgo": factores_riesgo,
                "SpO2 (%)": spo2 if respiratorio_valorado else None,
                "Interpretación SpO2": interpretacion_spo2 if respiratorio_valorado else "No valorado",
                "Frecuencia respiratoria (rpm)": resultado_fr.valor_rpm,
                "Interpretación FR": resultado_fr.interpretacion,
                "Regla FR": resultado_fr.regla_id,
                "Estado validación FR": resultado_fr.estado_validacion.value,
                "ID dato primario FR": resultado_fr.id_dato_primario,
                "Oxígeno suplementario": oxigeno_suplementario if respiratorio_valorado else "No valorado",
                "Puntaje Braden": puntaje_braden if braden_valorado else "No valorado",
                "Interpretación Braden": riesgo_braden if braden_valorado else "No valorado",
                "EVA dolor": eva_dolor if eva_valorado else "No valorado",
                "Interpretación EVA": interpretacion_eva if eva_valorado else "No valorado",
                "Puntaje riesgo de caídas": puntaje_caidas if caidas_valorado else "No valorado",
                "Interpretación riesgo de caídas": riesgo_caidas if caidas_valorado else "No valorado",
                "Semanas de gestación": semanas_gestacion if tipo_paciente == "Obstétrico" else "No aplica",
                "Gestas": gestas if tipo_paciente == "Obstétrico" else "No aplica",
                "PA obstétrica (mmHg)": f"{pas_texto}/{pad_texto}" if tipo_paciente == "Obstétrico" else "No aplica",
                "Interpretación PA obstétrica": interpretacion_pa_obstetrica,
                "Temperatura (°C)": temperatura if tipo_paciente == "Obstétrico" else "No aplica",
                "Movimientos fetales": movimientos_fetales if tipo_paciente == "Obstétrico" else "No aplica",
                "Ruta obstétrica activada": resumen_rutas_obstetricas if tipo_paciente == "Obstétrico" else "No aplica",
                "Clasificación RPM/infección": categorias_rpm if tipo_paciente == "Obstétrico" else "No aplica",
                "Hallazgos estructurados": ", ".join(hallazgos_seleccionados),
                "Datos clínicos texto libre": sintomas,
            }
            datos_paciente = actualizar_datos_paciente_glasgow(
                datos_paciente, resultado_glasgow
            )

            if tipo_paciente == "Recién nacido":
                datos_paciente["APGAR"] = serializar_resultado(resultado_apgar)
                datos_paciente["Silverman-Andersen"] = serializar_resultado(resultado_silverman)
                datos_paciente[f"Capurro {variante_capurro}"] = serializar_resultado(resultado_capurro)

            # Valores efectivos: solo entra al motor de alertas si la escala fue valorada
            _spo2_ef = spo2 if respiratorio_valorado else None
            _eva_ef = eva_dolor if eva_valorado else 0
            _braden_ef = puntaje_braden if braden_valorado else 23
            _glasgow_ef = resultado_glasgow.total
            _caidas_ef = puntaje_caidas if caidas_valorado else 0
            _rcaidas_ef = riesgo_caidas if caidas_valorado else "No valorado"

            # Alertas clínicas generales
            alertas_clinicas = generar_alertas_clinicas(
                spo2=_spo2_ef, fr=resultado_fr.valor_rpm, eva_dolor=_eva_ef,
                puntaje_braden=_braden_ef, glasgow_total=_glasgow_ef,
                puntaje_caidas=_caidas_ef, riesgo_caidas=_rcaidas_ef,
                hallazgos_seleccionados=hallazgos_seleccionados,
                resultado_fr=resultado_fr,
                resultado_glasgow=resultado_glasgow,
            )

            # Alerta EVA v18.1
            if tipo_paciente == "Obstétrico" and bool(dolor_abdominal_intenso) and (not eva_valorado or int(eva_dolor) == 0):
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
                movimientos_fetales=movimientos_fetales,
                nausea_vomito_persistente=nausea_vomito_persistente,
                disuria_obstetrica=disuria_obstetrica,
            )
            alertas_clinicas.extend(alertas_obstetricas)
            datos_paciente["Alertas clínicas educativas"] = alertas_a_texto(alertas_clinicas)

            # Buscar diagnósticos
            df_resultados = buscar_diagnosticos(
                texto_clinico,
                nanda_df,
                enlaces_df,
                dato_fetal_referido=movimientos_fetales in {"Disminuidos", "Ausentes"},
                evidencias=evidencias_clinicas,
            )
            df_resultados.attrs["estado_parsing"] = (
                "PARSING_NO_CONFIABLE"
                if "PARSING_NO_CONFIABLE" in estados_parsing
                else "PARSING_CONFIABLE"
            )
            df_resultados = enriquecer_plan(df_resultados, metas_df, noc_indicadores_df, nic_actividades_df, fundamentos_df)

        # Persistimos todo en session_state: sin esto, cualquier interacción
        # posterior (escribir una justificación, mover un toggle) reinicia
        # st.button a False y todo este resultado desaparecía de pantalla.
        st.session_state.plan_generado = True
        st.session_state.df_resultados = df_resultados
        st.session_state.datos_paciente = datos_paciente
        st.session_state.alertas_clinicas = alertas_clinicas
        st.session_state.valoracion_generada = valoracion_actual
        st.session_state.resultados_invalidados = False
        # Cada generación completada abre un intento independiente, incluso
        # con la misma valoración y los mismos códigos diagnósticos.
        for clave in list(st.session_state):
            if clave.startswith("justif_"):
                del st.session_state[clave]
        st.session_state.intento_id = uuid4().hex
        st.session_state.justificaciones = {}

    if st.session_state.get("resultados_invalidados"):
        st.warning(
            "La valoración cambió. Los resultados anteriores dejaron de ser válidos. "
            "Pulsa Generar Plan de Cuidados para regenerar antes de consultar o exportar resultados."
        )

    if st.session_state.get("plan_generado"):
        df_resultados = st.session_state.df_resultados
        datos_paciente = actualizar_datos_paciente_glasgow(
            st.session_state.datos_paciente, resultado_glasgow
        )
        alertas_clinicas = sincronizar_alertas_glasgow(
            st.session_state.alertas_clinicas, resultado_glasgow
        )
        st.session_state.datos_paciente = datos_paciente
        st.session_state.alertas_clinicas = alertas_clinicas

        # La comparación previa garantiza que estas entradas pertenecen a la
        # misma valoración que los datos, sugerencias y alertas almacenados.
        _spo2_ef = spo2 if respiratorio_valorado else None
        _eva_ef = eva_dolor if eva_valorado else 0
        _braden_ef = puntaje_braden if braden_valorado else 23
        _glasgow_ef = resultado_glasgow.total
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
            otras_alertas = [a for a in alertas_clinicas if a["Nivel"] != "Alta"]
            for alerta in alertas_altas:
                st.error(f"**[ALTA] {alerta['Área']}** — {alerta['Alerta']}  \n_{alerta['Acción sugerida']}_")
            for alerta in otras_alertas:
                nivel_visible = str(alerta["Nivel"]).upper()
                st.warning(f"**[{nivel_visible}] {alerta['Área']}** — {alerta['Alerta']}  \n_{alerta['Acción sugerida']}_")
        else:
            st.success("Sin alertas educativas críticas detectadas con los datos ingresados.")

        st.markdown("---")

        # =========================
        # DIAGNÓSTICOS
        # =========================
        advertencia_evidencia = df_resultados.attrs.get("advertencia_evidencia", "")
        if advertencia_evidencia:
            st.warning(advertencia_evidencia)
        if df_resultados.attrs.get("estado_parsing") == "PARSING_NO_CONFIABLE":
            st.warning(
                "Una mención del texto libre no pudo clasificarse con confiabilidad y "
                "se excluyó del puntaje automático. Los datos estructurados se conservaron."
            )
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
                resultado_fr.valor_rpm, resultado_fr.interpretacion,
                hallazgos_seleccionados,
                resultado_fr=resultado_fr,
                resultado_glasgow=resultado_glasgow,
            )
            st.info(resumen_clinico)
            datos_paciente["Resumen clínico educativo"] = resumen_clinico

            dx_principales = df_resultados[df_resultados["Jerarquía"] == "Principal"]
            dx_complementarios = df_resultados[df_resultados["Jerarquía"] == "Complementario"]

            col_dxa, col_dxb = st.columns(2)
            with col_dxa:
                st.subheader("Sugerencias diagnósticas principales")
                if dx_principales.empty:
                    st.info("Sin sugerencias diagnósticas principales con puntaje alto.")
                else:
                    cols_tabla = ["Código", "NANDA", "Puntaje", "Confianza", "Prioridad"]
                    st.dataframe(dx_principales[cols_tabla], use_container_width=True, hide_index=True)

            with col_dxb:
                st.subheader("Sugerencias diagnósticas complementarias")
                if dx_complementarios.empty:
                    st.info("Sin sugerencias diagnósticas complementarias.")
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
                key_base = f"justif_{st.session_state.intento_id}_{codigo_dx}"

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
            analisis_sesion = analizar_sesion(justificaciones_actuales, datos_paciente)
            word_docente = generar_word_docente(
                df_resultados, datos_paciente, justificaciones_actuales, analisis_sesion
            )

            col_xl, col_wd, col_doc = st.columns(3)
            with col_xl:
                st.download_button(
                    label="📊 Descargar Excel",
                    data=excel_file,
                    file_name="plan_cuidados_nnn_v1_rc1.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            with col_wd:
                st.download_button(
                    label="📄 Descargar Word",
                    data=word_file,
                    file_name="plan_cuidados_nnn_v1_rc1.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
            with col_doc:
                st.download_button(
                    label="🧑‍🏫 Reporte docente",
                    data=word_docente,
                    file_name="reporte_docente_sesion.docx",
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
    st.caption("KIKE-NNN v1.0.0-rc1 | Uso educativo exclusivo | Escuela de Enfermería y Obstetricia Leininger · Xalapa, Veracruz | No certificado por COFEPRIS")
