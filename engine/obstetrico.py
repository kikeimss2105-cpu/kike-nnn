"""
Módulo extraído de app.py v19 (KIKE-NNN) como parte de la separación
Datos -> Hallazgos -> Riesgos -> Diagnosticos -> NOC/NIC.

Las reglas son educativas, reproducibles y no emiten diagnósticos definitivos.
Los datos ausentes permanecen como ``None`` y nunca se convierten en cero.
"""


def _alcanza(valor, umbral):
    return valor is not None and valor >= umbral


def _menor_que(valor, umbral):
    return valor is not None and valor < umbral


def _pa_texto(pas, pad):
    sistolica = "no valorada" if pas is None else str(pas)
    diastolica = "no valorada" if pad is None else str(pad)
    return f"{sistolica}/{diastolica}"


def extraer_hallazgos_obstetricos(
    tipo_paciente,
    semanas_gestacion=None,
    pas=None,
    pad=None,
    temperatura=None,
    cefalea_intensa=False,
    fosfenos=False,
    acufenos=False,
    epigastralgia=False,
    edema_cara_manos=False,
    convulsiones=False,
    sangrado_vaginal=False,
    salida_liquido=False,
    liquido_fetido=False,
    liquido_verdoso=False,
    dolor_abdominal_intenso=False,
    contracciones_antes_termino=False,
    disminucion_mov_fetales=False,
    movimientos_fetales="No aplica / no valorado",
    nausea_vomito_persistente=False,
    disuria_obstetrica=False,
):
    """Normaliza solo datos observados y riesgos explícitos, sin diagnosticar."""
    if tipo_paciente != "Obstétrico":
        return []

    hallazgos = ["embarazo", "paciente obstétrica", "vigilancia obstétrica"]
    contexto_gestacional = _alcanza(semanas_gestacion, 20)
    pa_elevada = _alcanza(pas, 140) or _alcanza(pad, 90)
    pa_severa = _alcanza(pas, 160) or _alcanza(pad, 110)

    if contexto_gestacional:
        hallazgos.append("embarazo mayor de 20 semanas")
    if pa_elevada:
        hallazgos.append("presión arterial elevada")
        if contexto_gestacional:
            hallazgos.append("requiere evaluación de trastorno hipertensivo del embarazo")
    if pa_severa:
        hallazgos.extend(["hipertensión severa", "prioridad alta", "signos de alarma obstétrica"])
    if cefalea_intensa:
        hallazgos.extend(["cefalea intensa", "signos de alarma obstétrica"])
    if fosfenos:
        hallazgos.extend(["fosfenos", "visión borrosa", "signos de alarma obstétrica"])
    if acufenos:
        hallazgos.extend(["acúfenos", "zumbido de oídos", "signos de alarma obstétrica"])
    if epigastralgia:
        hallazgos.extend(["epigastralgia", "dolor epigástrico", "signos de alarma obstétrica"])
    if edema_cara_manos:
        hallazgos.extend(["edema", "edema de cara", "edema de manos"])
    if convulsiones:
        hallazgos.extend(["convulsiones", "alteración neurológica", "prioridad alta"])
    if sangrado_vaginal:
        hallazgos.append("sangrado vaginal")
    if salida_liquido:
        hallazgos.extend([
            "salida de líquido transvaginal",
            "sospecha de ruptura de membranas",
            "requiere valoración obstétrica",
        ])
    if liquido_fetido:
        hallazgos.extend(["líquido fétido", "posible riesgo de infección"])
    if liquido_verdoso:
        hallazgos.extend(["líquido verdoso", "requiere valoración de bienestar fetal"])
    if _alcanza(temperatura, 38):
        hallazgos.extend(["fiebre", "temperatura elevada", "posible riesgo de infección"])
    if dolor_abdominal_intenso:
        hallazgos.extend(["dolor abdominal intenso", "dolor agudo", "prioridad alta"])
    if contracciones_antes_termino:
        hallazgos.append("contracciones uterinas")
        if _menor_que(semanas_gestacion, 37):
            hallazgos.append("contracciones antes de término")
    movimientos_alterados = disminucion_mov_fetales or movimientos_fetales in {"Disminuidos", "Ausentes"}
    if contexto_gestacional and movimientos_alterados:
        hallazgos.extend([
            "disminución de movimientos fetales",
            "requiere valoración de bienestar fetal",
            "prioridad alta",
        ])
    if nausea_vomito_persistente:
        hallazgos.extend(["náusea", "vómito persistente", "requiere valoración de hidratación"])
    if disuria_obstetrica:
        hallazgos.extend(["disuria", "dolor al orinar", "posible riesgo urinario"])

    return list(dict.fromkeys(hallazgos))


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

    pa_severa = _alcanza(pas, 160) or _alcanza(pad, 110)
    pa_elevada = _alcanza(pas, 140) or _alcanza(pad, 90)

    if pa_severa:
        alertas.append({
            "Nivel": "Alta",
            "Área": "Obstétrico / hipertensión",
            "Alerta": f"PA {_pa_texto(pas, pad)} mmHg en rango severo.",
            "Acción sugerida": "Repetir medición si procede, mantener vigilancia, valorar datos de severidad y notificar de inmediato según protocolo."
        })
    elif pa_elevada:
        contexto_gestacional = _alcanza(semanas_gestacion, 20)
        nivel = "Alta" if contexto_gestacional and datos_neuro else "Media"
        alertas.append({
            "Nivel": nivel,
            "Área": "Obstétrico / hipertensión",
            "Alerta": f"PA {_pa_texto(pas, pad)} mmHg elevada en paciente obstétrica.",
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
            "Nivel": "Requiere valoración",
            "Área": "Obstétrico / sangrado",
            "Alerta": "Sangrado vaginal durante el embarazo: requiere valoración obstétrica y caracterización.",
            "Acción sugerida": "Valorar cantidad y características del sangrado, dolor observado, signos vitales y edad gestacional según protocolo."
        })

    if salida_liquido:
        nivel = "Alta" if _menor_que(semanas_gestacion, 37) else "Media"
        alertas.append({
            "Nivel": nivel,
            "Área": "Obstétrico / salida de líquido",
            "Alerta": "Salida de líquido transvaginal: sospecha de ruptura de membranas que requiere valoración.",
            "Acción sugerida": "Registrar hora, color, olor, cantidad, fiebre, dolor, movimientos fetales y referir/avisar según protocolo."
        })

    fiebre_medida = _alcanza(temperatura, 38)
    if liquido_fetido or liquido_verdoso or fiebre_medida:
        datos_registrados = []
        if fiebre_medida:
            datos_registrados.append(f"fiebre {temperatura}°C")
        if liquido_fetido:
            datos_registrados.append("líquido fétido")
        if liquido_verdoso:
            datos_registrados.append("líquido verdoso")
        alertas.append({
            "Nivel": "Alta",
            "Área": "Obstétrico / riesgo infeccioso o bienestar fetal",
            "Alerta": f"Datos de alarma registrados: {', '.join(datos_registrados)}.",
            "Acción sugerida": "Valorar posible riesgo infeccioso y estado materno-fetal; notificar según protocolo."
        })

    if dolor_abdominal_intenso:
        alertas.append({
            "Nivel": "Alta",
            "Área": "Obstétrico / dolor abdominal",
            "Alerta": "Dolor abdominal intenso en paciente obstétrica.",
            "Acción sugerida": "Valorar sangrado, dinámica uterina, signos vitales, edad gestacional y protocolo de urgencia obstétrica."
        })

    if contracciones_antes_termino and _menor_que(semanas_gestacion, 37):
        alertas.append({
            "Nivel": "Media",
            "Área": "Obstétrico / parto pretérmino",
            "Alerta": "Contracciones antes de las 37 semanas.",
            "Acción sugerida": "Valorar frecuencia, duración, dolor, salida de líquido, sangrado y protocolo de amenaza de parto pretérmino."
        })

    if disminucion_mov_fetales and _alcanza(semanas_gestacion, 20):
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


def evaluar_rutas_obstetricas(tipo_paciente, semanas_gestacion=None, pa_sistolica=None, pa_diastolica=None,
                              temperatura=None, cefalea=False, fosfenos=False, acufenos=False,
                              epigastralgia=False, edema=False, convulsiones=False,
                              sangrado=False, salida_liquido=False, liquido_fetido=False,
                              liquido_verdoso=False, dolor_abdominal=False,
                              contracciones=False, movimientos_fetales="No aplica / no valorado",
                              hallazgos_detectados=None):
    """
    Clasifica señales obstétricas por ruta educativa.
    v18.1:
    - Separa dolor obstétrico de hemorragia.
    - No clasifica un sangrado aislado como hemorragia o choque.
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

    contexto_gestacional = _alcanza(semanas_gestacion, 20)
    pa_elevada = contexto_gestacional and (
        _alcanza(pa_sistolica, 140) or _alcanza(pa_diastolica, 90)
    )
    pa_severa = _alcanza(pa_sistolica, 160) or _alcanza(pa_diastolica, 110)

    if pa_elevada:
        datos_hipertensivos.append(f"PA {pa_sistolica}/{pa_diastolica} desde semana 20 o más")
    elif tiene("hipertensión", "hipertension", "preeclampsia"):
        datos_hipertensivos.append("hallazgo referido de trastorno hipertensivo")

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
            "Ruta": "Evaluación de trastorno hipertensivo",
            "Nivel": nivel,
            "Datos activadores": ", ".join(datos_hipertensivos),
            "Acción educativa": "Valorar signos de severidad, proteinuria si procede, bienestar fetal y activar protocolo institucional."
        })
        if contexto_gestacional:
            datos.append("evaluación de trastorno hipertensivo del embarazo")
        else:
            datos.append("evaluación obstétrica por presión arterial o signos de alarma")
        datos.extend(["signos de alarma obstétrica", "requiere valoración obstétrica"])

    # =========================
    # RUTA RPM / INFECCIÓN
    # =========================
    datos_rpm = []
    sospecha_rpm = salida_liquido or tiene(
        "salida de líquido", "salida de liquido", "ruptura de membranas", "rpm"
    )
    if sospecha_rpm:
        datos_rpm.append("salida de líquido transvaginal")
    if liquido_fetido or tiene("líquido fétido", "liquido fetido", "mal olor"):
        datos_rpm.append("líquido fétido")
    if liquido_verdoso or tiene("líquido verdoso", "liquido verdoso", "meconio"):
        datos_rpm.append("líquido verdoso")
    fiebre_medida = _alcanza(temperatura, 38)
    if fiebre_medida or tiene("fiebre"):
        datos_rpm.append(f"fiebre {temperatura}°C" if fiebre_medida else "fiebre referida")

    if datos_rpm:
        nivel = "Alta" if (
            liquido_fetido or fiebre_medida or liquido_verdoso or
            tiene("líquido fétido", "liquido fetido", "fiebre", "líquido verdoso", "liquido verdoso")
        ) else "Media"
        datos_rpm = list(dict.fromkeys(datos_rpm))
        nombre_ruta = (
            "Sospecha de ruptura de membranas / riesgo infeccioso"
            if sospecha_rpm
            else "Evaluación de riesgo infeccioso obstétrico"
        )
        rutas.append({
            "Ruta": nombre_ruta,
            "Nivel": nivel,
            "Datos activadores": ", ".join(datos_rpm),
            "Acción educativa": "Valorar posible ruptura de membranas, temperatura, características del líquido, dolor, bienestar fetal y posible riesgo infeccioso según protocolo."
        })
        if sospecha_rpm:
            datos.extend(["salida de líquido transvaginal", "sospecha de ruptura de membranas"])
        if liquido_fetido or liquido_verdoso or fiebre_medida or tiene(
            "líquido fétido", "liquido fetido", "fiebre", "líquido verdoso", "liquido verdoso"
        ):
            datos.append("posible riesgo de infección")
        datos.extend(["vigilancia obstétrica", "requiere valoración obstétrica"])

    # =========================
    # RUTA DE VALORACIÓN DE SANGRADO OBSTÉTRICO
    # Conserva la localización solo cuando fue observada explícitamente.
    # =========================
    datos_hemorragicos = []
    sangrado_vaginal_observado = bool(sangrado) or tiene_exacto("sangrado vaginal")
    sangrado_general_observado = tiene_exacto("hemorragia", "sangrado obstétrico")
    sangrado_real = sangrado_vaginal_observado or sangrado_general_observado
    if sangrado_real:
        if sangrado_vaginal_observado:
            datos_hemorragicos.append("sangrado vaginal")
        if tiene_exacto("hemorragia"):
            datos_hemorragicos.append("hemorragia")
        if tiene_exacto("sangrado obstétrico"):
            datos_hemorragicos.append("sangrado obstétrico")
        if dolor_abdominal or tiene("dolor abdominal", "dolor uterino"):
            datos_hemorragicos.append("dolor abdominal")
        contracciones_pretermino = _menor_que(semanas_gestacion, 37) and (
            contracciones or tiene("contracciones antes de término", "contracciones antes de termino")
        )
        if contracciones_pretermino:
            datos_hemorragicos.append("contracciones antes de término")

        datos_hemorragicos = list(dict.fromkeys(datos_hemorragicos))
        rutas.append({
            "Ruta": "Sangrado obstétrico / requiere valoración",
            "Nivel": "Requiere valoración",
            "Datos activadores": ", ".join(datos_hemorragicos),
            "Acción educativa": "Caracterizar el sangrado y valorar dolor observado, signos vitales, edad gestacional y tono uterino según protocolo."
        })
        datos.extend(datos_hemorragicos)

    # =========================
    # RUTA DOLOR OBSTÉTRICO / SIGNO DE ALARMA
    # Dolor sin sangrado no debe contaminar como hemorragia.
    # =========================
    datos_dolor = []
    if dolor_abdominal or tiene("dolor abdominal", "dolor uterino"):
        datos_dolor.append("dolor abdominal/uterino")
    contracciones_pretermino = _menor_que(semanas_gestacion, 37) and (
        contracciones or tiene("contracciones antes de término", "contracciones antes de termino")
    )
    if contracciones_pretermino:
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
    edad_para_movimientos = _alcanza(semanas_gestacion, 20)
    if edad_para_movimientos and movimientos_fetales in ["Disminuidos", "Ausentes"]:
        datos_fetales.append(f"movimientos fetales {movimientos_fetales.lower()}")
    if edad_para_movimientos and tiene("disminución de movimientos fetales", "disminucion de movimientos fetales", "movimientos fetales disminuidos", "movimientos fetales ausentes"):
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
            "requiere valoración de bienestar fetal",
            "signos de alarma obstétrica"
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
