"""
Módulo extraído de app.py v19 (KIKE-NNN) como parte de la separación
Datos -> Hallazgos -> Riesgos -> Diagnosticos -> NOC/NIC.

Lógica de negocio verificada byte-a-byte contra el comportamiento original
mediante tests/test_golden.py antes de sustituir el código en app.py.
"""


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
