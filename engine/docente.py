"""
Análisis docente de una sesión de razonamiento clínico (Nivel 1 del plan).

Toma las decisiones y argumentos del estudiante (módulo de justificación
clínica) y produce un análisis basado en REGLAS EXPLÍCITAS — sin IA —
pensado para el docente:

  1. Señales por diagnóstico: qué decisiones merecen revisión en clase.
  2. Áreas de oportunidad de la sesión: patrones agregados del desempeño.

Límite honesto de este módulo (declarado a propósito):
La app sugiere diagnósticos por coincidencia de texto; NO tiene una clave
de respuesta validada por caso (eso llega con el banco de casos, Nivel 2).
Por lo tanto este análisis NUNCA afirma que el alumno "se equivocó" —
solo señala qué conviene revisar con él. Rechazar un diagnóstico Principal
con un argumento sólido puede ser un acto de buen juicio clínico, no un error.
"""

# Umbral mínimo (en caracteres) para considerar que un argumento tiene
# desarrollo suficiente. ~60 caracteres equivale a una oración corta real.
ARGUMENTO_MINIMO = 60


def _analizar_diagnostico(nanda, datos):
    """Genera las señales de revisión para una decisión individual."""
    decision = datos.get("decision", "Sin decidir")
    jerarquia = datos.get("jerarquia", "")
    criterios = datos.get("criterios", []) or []
    argumento = (datos.get("justificacion", "") or "").strip()

    senales = []

    if decision == "Sin decidir":
        senales.append("Quedó sin decisión: el ciclo de razonamiento no se completó para este diagnóstico.")
        return {
            "nanda": nanda, "decision": decision, "jerarquia": jerarquia,
            "confianza": datos.get("confianza", ""),
            "n_criterios": len(criterios), "longitud_argumento": len(argumento),
            "senales": senales,
        }

    if not criterios:
        senales.append(
            "Decisión sin criterios clínicos seleccionados: no ancló su postura en "
            "características definitorias ni factores relacionados."
        )

    if not argumento:
        senales.append("Decisión sin argumento escrito.")
    elif len(argumento) < ARGUMENTO_MINIMO:
        senales.append(
            f"Argumento breve ({len(argumento)} caracteres): posible justificación "
            "superficial, vale la pena pedirle que la desarrolle."
        )

    if jerarquia == "Principal" and decision == "Rechazado":
        if len(argumento) >= ARGUMENTO_MINIMO and criterios:
            senales.append(
                "Rechazó un diagnóstico sugerido como Principal, con argumento y criterios: "
                "revisar en clase — puede ser un acierto de juicio clínico o un área de refuerzo."
            )
        else:
            senales.append(
                "Rechazó un diagnóstico sugerido como Principal sin sustento completo: "
                "prioridad de revisión con el alumno."
            )

    return {
        "nanda": nanda, "decision": decision, "jerarquia": jerarquia,
        "confianza": datos.get("confianza", ""),
        "n_criterios": len(criterios), "longitud_argumento": len(argumento),
        "senales": senales,
    }


def analizar_sesion(justificaciones):
    """Análisis completo de una sesión para el reporte docente.

    justificaciones: dict {nanda: {decision, confianza, jerarquia, puntaje,
                                    criterios: list, justificacion: str}}
    Devuelve dict con: resumen (conteos), por_diagnostico (lista de análisis
    individuales) y areas_oportunidad (lista de textos agregados).
    """
    if not justificaciones:
        return {
            "resumen": {"total": 0, "aceptados": 0, "rechazados": 0, "sin_decidir": 0},
            "por_diagnostico": [],
            "areas_oportunidad": ["No hay decisiones registradas en esta sesión."],
        }

    por_dx = [_analizar_diagnostico(nanda, datos) for nanda, datos in justificaciones.items()]

    total = len(por_dx)
    aceptados = sum(1 for d in por_dx if d["decision"] == "Aceptado")
    rechazados = sum(1 for d in por_dx if d["decision"] == "Rechazado")
    sin_decidir = sum(1 for d in por_dx if d["decision"] == "Sin decidir")
    decididos = aceptados + rechazados

    sin_criterios = sum(1 for d in por_dx if d["decision"] != "Sin decidir" and d["n_criterios"] == 0)
    argumento_debil = sum(
        1 for d in por_dx
        if d["decision"] != "Sin decidir" and d["longitud_argumento"] < ARGUMENTO_MINIMO
    )

    areas = []

    if sin_decidir > 0:
        areas.append(
            f"Cierre del ciclo de decisión: {sin_decidir} de {total} diagnósticos quedaron sin "
            "decidir. Reforzar que todo diagnóstico sugerido exige una postura argumentada, "
            "incluso para rechazarlo."
        )

    if decididos > 0 and sin_criterios > 0:
        areas.append(
            f"Anclaje en criterios NANDA: {sin_criterios} de {decididos} decisiones se tomaron "
            "sin seleccionar características definitorias ni factores relacionados. Reforzar el "
            "vínculo dato clínico → criterio → diagnóstico."
        )

    if decididos > 0 and argumento_debil > 0:
        areas.append(
            f"Profundidad de argumentación: {argumento_debil} de {decididos} decisiones tienen "
            "argumento ausente o breve. Trabajar la estructura dato–criterio–conclusión en la "
            "justificación escrita."
        )

    if total >= 3 and rechazados == 0 and sin_decidir == 0:
        areas.append(
            "Discriminación diagnóstica: aceptó todos los diagnósticos sugeridos. Revisar si "
            "está evaluando críticamente cada sugerencia o validando de forma automática lo que "
            "propone la herramienta."
        )

    if total >= 3 and aceptados == 0 and sin_decidir == 0:
        areas.append(
            "Rechazo total de sugerencias: rechazó todos los diagnósticos. Revisar sus argumentos "
            "en clase — puede indicar criterio sólido frente a sugerencias que no aplican, o una "
            "dificultad para reconocer diagnósticos pertinentes."
        )

    if not areas:
        areas.append(
            "Sesión completa: todas las decisiones cerradas, con criterios y argumento "
            "desarrollado. Revisar la calidad clínica de los argumentos directamente en la "
            "sección por diagnóstico."
        )

    return {
        "resumen": {
            "total": total, "aceptados": aceptados,
            "rechazados": rechazados, "sin_decidir": sin_decidir,
        },
        "por_diagnostico": por_dx,
        "areas_oportunidad": areas,
    }
