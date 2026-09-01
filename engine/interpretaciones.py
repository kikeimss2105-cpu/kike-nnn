"""
Módulo extraído de app.py v19 (KIKE-NNN) como parte de la separación
Datos -> Hallazgos -> Riesgos -> Diagnosticos -> NOC/NIC.

Lógica de negocio verificada byte-a-byte contra el comportamiento original
mediante tests/test_golden.py antes de sustituir el código en app.py.
"""


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
    from engine.glasgow import interpretar_total_glasgow

    return interpretar_total_glasgow(glasgow)


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
    from engine.respiratorio import evaluar_fr

    resultado = evaluar_fr(fr, valorado=fr is not None, perfil="Adulto")
    return resultado.interpretacion


def interpretar_fr_por_tipo(fr, tipo_paciente):
    """Interpretación educativa de FR según perfil. Ajustar siempre a edad exacta y protocolo."""
    from engine.respiratorio import evaluar_fr

    resultado = evaluar_fr(fr, valorado=fr is not None, perfil=tipo_paciente)
    return resultado.interpretacion


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
    if pas is None and pad is None:
        return "PA no valorada: faltan presión sistólica y diastólica"
    if (pas is not None and pas >= 160) or (pad is not None and pad >= 110):
        return "PA en rango severo: requiere valoración urgente según protocolo obstétrico"
    if (pas is not None and pas >= 140) or (pad is not None and pad >= 90):
        if semanas_gestacion is not None and semanas_gestacion >= 20:
            return "PA elevada desde semana 20 o más: vigilar datos compatibles con trastorno hipertensivo del embarazo"
        return "PA elevada en embarazo: requiere vigilancia y validación clínica"
    if pas is None or pad is None:
        return "PA parcialmente valorada: falta una de las mediciones"
    return "Sin umbral de PA elevada en este tamizaje"
