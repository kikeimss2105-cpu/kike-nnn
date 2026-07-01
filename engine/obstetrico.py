"""
Módulo extraído de app.py v19 (KIKE-NNN) como parte de la separación
Datos -> Hallazgos -> Riesgos -> Diagnosticos -> NOC/NIC.

Lógica de negocio verificada byte-a-byte contra el comportamiento original
mediante tests/test_golden.py antes de sustituir el código en app.py.
"""


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
