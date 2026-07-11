"""
Golden tests — autocontenidos, sin dependencias fuera de este repo.

Estos valores esperados fueron verificados el 2026-06-30 comparando
byte-a-byte el motor original de app.py (v19, pre-refactor) contra
engine/ (528/528 pruebas pasadas). Este archivo NO depende de app.py
original (ya no existe tras el refactor) — es la referencia fija de
aquí en adelante para detectar regresiones futuras.

Uso:
    cd ~/ProyectosIA/kike-nnn-v19   (o la ruta de tu repo)
    python3 tests/test_golden.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.carga import cargar_catalogos
from engine.texto import normalizar_texto, separar_lista
from engine.motor import buscar_diagnosticos, nivel_confianza
from engine.plan import enriquecer_plan, obtener_meta_nanda
from engine.interpretaciones import (
    interpretar_braden, interpretar_eva, interpretar_glasgow,
    interpretar_riesgo_caidas, interpretar_spo2, interpretar_fr_adulto,
    interpretar_fr_por_tipo, interpretar_pa_obstetrica,
)
from engine.obstetrico import evaluar_rutas_obstetricas
from engine.resumen import generar_resumen_clinico, generar_alertas_clinicas, alertas_a_texto

fallos = []
ok = 0


def check(nombre, esperado, obtenido):
    global ok
    if esperado != obtenido:
        fallos.append((nombre, esperado, obtenido))
    else:
        ok += 1


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CAT = cargar_catalogos(data_dir=DATA_DIR)

# ---------------------------------------------------------------
# Texto
# ---------------------------------------------------------------
check("normalizar_texto acentos", "preeclampsia severa", normalizar_texto("PREECLAMPSIA severa"))
check("normalizar_texto None", "", normalizar_texto(None))
check("separar_lista básico", ["disnea", "cianosis"], separar_lista("Disnea;Cianosis"))
check("separar_lista vacío", [], separar_lista(None))

# ---------------------------------------------------------------
# Interpretaciones de escalas — valores fijos conocidos
# ---------------------------------------------------------------
check("braden 9", "Riesgo muy alto", interpretar_braden(9))
check("braden 12", "Riesgo alto", interpretar_braden(12))
check("braden 14", "Riesgo moderado", interpretar_braden(14))
check("braden 18", "Riesgo leve", interpretar_braden(18))
check("braden 20", "Sin riesgo significativo", interpretar_braden(20))

check("eva 0", "Sin dolor", interpretar_eva(0))
check("eva 3", "Dolor leve", interpretar_eva(3))
check("eva 6", "Dolor moderado", interpretar_eva(6))
check("eva 10", "Dolor intenso", interpretar_eva(10))

check("glasgow 8", "Compromiso neurológico grave", interpretar_glasgow(8))
check("glasgow 12", "Compromiso neurológico moderado", interpretar_glasgow(12))
check("glasgow 15", "Estado neurológico aparentemente conservado", interpretar_glasgow(15))

check("caidas 6", "Riesgo alto de caídas", interpretar_riesgo_caidas(6))
check("caidas 3", "Riesgo moderado de caídas", interpretar_riesgo_caidas(3))
check("caidas 0", "Sin riesgo evidente por este tamizaje", interpretar_riesgo_caidas(0))

check("spo2 90", "Saturación críticamente baja", interpretar_spo2(90))
check("spo2 95", "Saturación en vigilancia", interpretar_spo2(95))
check("spo2 98", "Saturación dentro de rango esperado", interpretar_spo2(98))

check("fr adulto 35", "Taquipnea marcada", interpretar_fr_adulto(35))
check("fr adulto 16", "Frecuencia respiratoria dentro de rango adulto esperado", interpretar_fr_adulto(16))

check("fr pediátrico 45", "Taquipnea pediátrica marcada", interpretar_fr_por_tipo(45, "Pediátrico"))
check("fr obstétrico 26", "Taquipnea: valorar signos de alarma obstétrica", interpretar_fr_por_tipo(26, "Obstétrico"))

check("pa obstétrica severa", "PA en rango severo: requiere valoración urgente según protocolo obstétrico",
      interpretar_pa_obstetrica(165, 112, 30))
check("pa obstétrica normal", "PA dentro de rango esperado por este tamizaje",
      interpretar_pa_obstetrica(110, 70, 30))

check("nivel_confianza alta", "Alta", nivel_confianza(12))
check("nivel_confianza media", "Media", nivel_confianza(8))
check("nivel_confianza sin coincidencia", "Sin coincidencia", nivel_confianza(0))

# ---------------------------------------------------------------
# Motor de búsqueda de diagnósticos (usa data/nanda.csv real)
# ---------------------------------------------------------------
df = buscar_diagnosticos("disnea cianosis saturación baja", CAT.nanda, CAT.enlaces)
resultado = df[["NANDA", "Puntaje", "Jerarquía"]].to_dict("records")
esperado = [
    {"NANDA": "Deterioro del intercambio gaseoso", "Puntaje": 12, "Jerarquía": "Principal"},
    {"NANDA": "Disminución del gasto cardíaco", "Puntaje": 8, "Jerarquía": "Complementario"},
]
check("buscar_diagnosticos: disnea/cianosis/sat baja", esperado, resultado)

df_vacio = buscar_diagnosticos("texto sin coincidencias xyz123", CAT.nanda, CAT.enlaces)
check("buscar_diagnosticos: sin coincidencias -> vacío", True, df_vacio.empty)

# ---------------------------------------------------------------
# Rutas obstétricas — las 5 rutas, casos fijos y verificados
# ---------------------------------------------------------------
casos_obst = [
    (dict(tipo_paciente="Adulto"), [], "No aplica"),
    (dict(tipo_paciente="Obstétrico", semanas_gestacion=25, pa_sistolica=150, pa_diastolica=95,
          cefalea=True, fosfenos=True),
     ['hipertensión', 'preeclampsia', 'signos de alarma obstétrica', 'riesgo de alteración de la díada materno-fetal'],
     '[Alta] Hipertensiva / preeclampsia: PA 150/95 desde semana 20 o más, cefalea, fosfenos/visión borrosa. '
     'Acción educativa: Valorar signos de severidad, proteinuria si procede, bienestar fetal y activar protocolo institucional.'),
    (dict(tipo_paciente="Obstétrico", semanas_gestacion=25, pa_sistolica=165, pa_diastolica=115, convulsiones=True),
     ['hipertensión', 'preeclampsia', 'signos de alarma obstétrica', 'riesgo de alteración de la díada materno-fetal'],
     '[Crítica] Hipertensiva / preeclampsia: PA 165/115 desde semana 20 o más, PA severa, convulsiones. '
     'Acción educativa: Valorar signos de severidad, proteinuria si procede, bienestar fetal y activar protocolo institucional.'),
    (dict(tipo_paciente="Obstétrico", semanas_gestacion=32, salida_liquido=True, liquido_fetido=True, temperatura=38.5),
     ['salida de líquido transvaginal', 'ruptura de membranas', 'riesgo de infección', 'vigilancia obstétrica', 'riesgo de infección materno-fetal'],
     '[Alta] RPM / infección: salida de líquido transvaginal, líquido fétido, fiebre 38.5°C. '
     'Acción educativa: Vigilar temperatura, características del líquido, dolor, bienestar fetal y riesgo infeccioso según protocolo.'),
    (dict(tipo_paciente="Obstétrico", semanas_gestacion=32, movimientos_fetales="Ausentes"),
     ['disminución de movimientos fetales', 'vigilancia fetal', 'estado fetal anteparto', 'riesgo de alteración de la díada materno-fetal'],
     '[Alta] Bienestar fetal: movimientos fetales ausentes. '
     'Acción educativa: Registrar movimientos fetales referidos y solicitar valoración de bienestar fetal según protocolo.'),
]
for i, (kwargs, datos_esp, resumen_esp) in enumerate(casos_obst):
    datos, resumen = evaluar_rutas_obstetricas(**kwargs)
    check(f"ruta obstétrica[{i}] datos", datos_esp, datos)
    check(f"ruta obstétrica[{i}] resumen", resumen_esp, resumen)

# ---------------------------------------------------------------
# Resumen clínico — escalas "No valorado" deben omitirse, no imprimirse
# (fix aplicado 2026-07-01: antes generar_resumen_clinico imprimía
#  "Escala de Braden: ... interpretación: No valorado." en vez de omitir
#  la línea completa cuando el toggle correspondiente estaba apagado.)
# ---------------------------------------------------------------
df_dx = buscar_diagnosticos("disnea cianosis saturación baja", CAT.nanda, CAT.enlaces)

resumen_normal = generar_resumen_clinico(
    df_resultados=df_dx,
    puntaje_braden=14, riesgo_braden="Riesgo moderado",
    eva_dolor=6, interpretacion_eva="Dolor moderado",
    glasgow_total=15, interpretacion_glasgow="Estado neurológico aparentemente conservado",
    puntaje_caidas=2, riesgo_caidas="Riesgo bajo de caídas",
    spo2=91, interpretacion_spo2="Saturación baja",
    fr=24, interpretacion_fr="Taquipnea",
    hallazgos=["disnea", "cianosis"],
)
check("resumen normal: incluye Braden", True, "Escala de Braden" in resumen_normal)
check("resumen normal: incluye EVA", True, "EVA del dolor" in resumen_normal)
check("resumen normal: incluye Glasgow", True, "Glasgow" in resumen_normal)
check("resumen normal: incluye caídas", True, "Riesgo de caídas" in resumen_normal)
check("resumen normal: incluye respiratorio", True, "Respiratorio" in resumen_normal)

resumen_no_valorado = generar_resumen_clinico(
    df_resultados=df_dx,
    puntaje_braden=0, riesgo_braden="No valorado",
    eva_dolor=0, interpretacion_eva="No valorado",
    glasgow_total=0, interpretacion_glasgow="No valorado",
    puntaje_caidas=0, riesgo_caidas="No valorado",
    spo2=98, interpretacion_spo2="No valorado",
    fr=18, interpretacion_fr="No valorado",
    hallazgos=["disnea", "cianosis"],
)
check("resumen sin valorar: OMITE Braden", False, "Braden" in resumen_no_valorado)
check("resumen sin valorar: OMITE EVA", False, "EVA del dolor" in resumen_no_valorado)
check("resumen sin valorar: OMITE Glasgow", False, "Glasgow" in resumen_no_valorado)
check("resumen sin valorar: OMITE caídas", False, "Riesgo de caídas" in resumen_no_valorado)
check("resumen sin valorar: OMITE respiratorio", False, "Respiratorio" in resumen_no_valorado)
check("resumen sin valorar: conserva diagnósticos", True, "Prioridad principal" in resumen_no_valorado)

resumen_mixto = generar_resumen_clinico(
    df_resultados=df_dx,
    puntaje_braden=14, riesgo_braden="Riesgo moderado",
    eva_dolor=0, interpretacion_eva="No valorado",
    glasgow_total=15, interpretacion_glasgow="Estado neurológico aparentemente conservado",
    puntaje_caidas=0, riesgo_caidas="No valorado",
    spo2=98, interpretacion_spo2="No valorado",
    fr=18, interpretacion_fr="No valorado",
    hallazgos=["disnea", "cianosis"],
)
check("resumen mixto: incluye Braden (sí valorado)", True, "Braden" in resumen_mixto)
check("resumen mixto: OMITE EVA (no valorado)", False, "EVA del dolor" in resumen_mixto)
check("resumen mixto: incluye Glasgow (sí valorado)", True, "Glasgow" in resumen_mixto)
check("resumen mixto: OMITE caídas (no valorado)", False, "Riesgo de caídas" in resumen_mixto)
check("resumen mixto: OMITE respiratorio (ninguno valorado)", False, "Respiratorio" in resumen_mixto)

# ---------------------------------------------------------------
# Alertas clínicas generales
# ---------------------------------------------------------------
alertas = generar_alertas_clinicas(
    spo2=89, fr=32, eva_dolor=8, puntaje_braden=10, glasgow_total=7,
    puntaje_caidas=7, riesgo_caidas="Riesgo alto de caídas",
    hallazgos_seleccionados=["fiebre", "herida"],
)
check("alertas críticas: cantidad", 7, len(alertas))
check("alertas críticas: primer nivel", "Alta", alertas[0]["Nivel"])

texto_alertas = alertas_a_texto(alertas)
check("alertas_a_texto no vacío", True, len(texto_alertas) > 0)

sin_alertas = generar_alertas_clinicas(
    spo2=98, fr=16, eva_dolor=2, puntaje_braden=20, glasgow_total=15,
    puntaje_caidas=0, riesgo_caidas="Sin riesgo evidente por este tamizaje",
    hallazgos_seleccionados=[],
)
check("sin alertas -> lista vacía", [], sin_alertas)
check("alertas_a_texto vacío", "Sin alertas educativas críticas detectadas con los datos ingresados.",
      alertas_a_texto(sin_alertas))


# ---------------------------------------------------------------
# Análisis docente (engine/docente.py) — reglas de señales y áreas
# ---------------------------------------------------------------
from engine.docente import analizar_sesion, ARGUMENTO_MINIMO

# Sesión vacía
a = analizar_sesion({})
check("docente: sesión vacía total 0", 0, a["resumen"]["total"])
check("docente: sesión vacía tiene mensaje", 1, len(a["areas_oportunidad"]))

# Sesión completa y sólida: sin señales, área única de "sesión completa"
justif_solida = {
    "Dolor agudo": {"decision": "Aceptado", "jerarquia": "Principal", "confianza": "Alta",
                     "criterios": ["expresión verbal de dolor"],
                     "justificacion": "La paciente refiere dolor 8/10 en epigastrio con facies álgica y taquicardia, compatible con las características definitorias."},
    "Riesgo de infección": {"decision": "Rechazado", "jerarquia": "Complementario", "confianza": "Media",
                             "criterios": ["procedimientos invasivos"],
                             "justificacion": "No hay datos de ruptura de membranas, fiebre ni procedimientos invasivos recientes en este caso; el riesgo no se sustenta."},
}
a = analizar_sesion(justif_solida)
check("docente: sólida sin señales dx1", [], a["por_diagnostico"][0]["senales"])
check("docente: sólida sin señales dx2", [], a["por_diagnostico"][1]["senales"])
check("docente: sólida área única", True, "Sesión completa" in a["areas_oportunidad"][0])

# Decisión sin criterios ni argumento
justif_debil = {
    "Dolor agudo": {"decision": "Aceptado", "jerarquia": "Principal", "confianza": "Alta",
                     "criterios": [], "justificacion": ""},
}
a = analizar_sesion(justif_debil)
senales = a["por_diagnostico"][0]["senales"]
check("docente: débil detecta sin criterios", True, any("sin criterios" in s for s in senales))
check("docente: débil detecta sin argumento", True, any("sin argumento" in s for s in senales))

# Argumento corto (bajo el umbral)
justif_corta = {
    "Dolor agudo": {"decision": "Aceptado", "jerarquia": "Principal", "confianza": "Alta",
                     "criterios": ["expresión verbal de dolor"], "justificacion": "porque le duele"},
}
a = analizar_sesion(justif_corta)
check("docente: argumento corto detectado", True,
      any("breve" in s for s in a["por_diagnostico"][0]["senales"]))

# Principal rechazado sin sustento vs con sustento
justif_principal_sin = {
    "Dolor agudo": {"decision": "Rechazado", "jerarquia": "Principal", "confianza": "Alta",
                     "criterios": [], "justificacion": ""},
}
a = analizar_sesion(justif_principal_sin)
check("docente: principal rechazado sin sustento -> prioridad", True,
      any("prioridad de revisión" in s for s in a["por_diagnostico"][0]["senales"]))

justif_principal_con = {
    "Dolor agudo": {"decision": "Rechazado", "jerarquia": "Principal", "confianza": "Alta",
                     "criterios": ["expresión verbal de dolor"],
                     "justificacion": "La paciente niega dolor en la valoración actual y no presenta facies álgica ni datos objetivos; el hallazgo del texto era de un turno anterior ya resuelto."},
}
a = analizar_sesion(justif_principal_con)
check("docente: principal rechazado con sustento -> acierto posible", True,
      any("acierto de juicio" in s for s in a["por_diagnostico"][0]["senales"]))

# Sin decidir
justif_pendiente = {
    "Dolor agudo": {"decision": "Sin decidir", "jerarquia": "Principal", "confianza": "Alta",
                     "criterios": [], "justificacion": ""},
}
a = analizar_sesion(justif_pendiente)
check("docente: sin decidir detectado", True,
      any("sin decisión" in s.lower() for s in a["por_diagnostico"][0]["senales"]))
check("docente: área cierre de ciclo", True,
      any("Cierre del ciclo" in area for area in a["areas_oportunidad"]))

# Aceptación indiscriminada (3+ dx, todo aceptado)
arg_largo = "Argumento suficientemente desarrollado para superar el umbral mínimo de caracteres del análisis."
justif_todo_si = {
    f"Dx{i}": {"decision": "Aceptado", "jerarquia": "Complementario", "confianza": "Media",
                "criterios": ["criterio"], "justificacion": arg_largo}
    for i in range(3)
}
a = analizar_sesion(justif_todo_si)
check("docente: aceptación indiscriminada detectada", True,
      any("Discriminación diagnóstica" in area for area in a["areas_oportunidad"]))



# Escalas sin valorar (idea de Kike: la omisión de valoración también es señal docente)
from engine.docente import detectar_escalas_sin_valorar

dp_completo = {"Interpretación Braden": "Riesgo moderado", "Interpretación EVA": "Dolor moderado",
               "Interpretación Glasgow": "Estado neurológico aparentemente conservado",
               "Interpretación riesgo de caídas": "Riesgo bajo de caídas",
               "Interpretación SpO2": "Saturación dentro de rango esperado"}
check("escalas: valoración completa -> vacío", [], detectar_escalas_sin_valorar(dp_completo))

dp_parcial = dict(dp_completo)
dp_parcial["Interpretación Braden"] = "No valorado"
dp_parcial["Interpretación Glasgow"] = "No valorado"
detectadas = detectar_escalas_sin_valorar(dp_parcial)
check("escalas: detecta 2 omitidas", 2, len(detectadas))
check("escalas: Braden detectada", True, any("Braden" in e for e in detectadas))
check("escalas: Glasgow detectada", True, any("Glasgow" in e for e in detectadas))
check("escalas: sin datos -> vacío", [], detectar_escalas_sin_valorar(None))

a = analizar_sesion(justif_solida, dp_parcial)
check("escalas: área de valoración instrumental presente", True,
      any("Valoración instrumental" in area for area in a["areas_oportunidad"]))
check("escalas: campo en retorno", 2, len(a["escalas_sin_valorar"]))

a = analizar_sesion(justif_solida, dp_completo)
check("escalas: completa no genera área instrumental", False,
      any("Valoración instrumental" in area for area in a["areas_oportunidad"]))



# ---------------------------------------------------------------
# Gordon — patrones funcionales, crosswalk y excepciones (Nivel Gordon)
# ---------------------------------------------------------------
from engine.gordon import cargar_patrones_gordon, hallazgos_desde_respuestas, cargar_crosswalk, cargar_excepciones, agrupar_nanda_por_patron

patrones_g = cargar_patrones_gordon(data_dir=str(DATA_DIR))
listos_g = [p for p in patrones_g if p.estado == "listo"]
check("gordon: 4 patrones listos", 4, len(listos_g))
check("gordon: 11 patrones totales", 11, len(patrones_g))

respuestas_g = {"peso_perdida": True, "apetito": True, "ingesta": True}
hallazgos_g = hallazgos_desde_respuestas(patrones_g, respuestas_g)
check("gordon: hallazgos generados", 3, len(hallazgos_g))
check("gordon: contiene pérdida de peso", True, "pérdida de peso" in hallazgos_g)

df_dx_gordon = buscar_diagnosticos(" ".join(hallazgos_g), CAT.nanda, CAT.enlaces)
check("gordon: dispara diagnóstico nutricional", True,
      "Desequilibrio nutricional inferior a las necesidades corporales" in df_dx_gordon["NANDA"].tolist())

crosswalk_g = cargar_crosswalk(data_dir=str(DATA_DIR))
excepciones_g = cargar_excepciones(data_dir=str(DATA_DIR))
agrupado_g = agrupar_nanda_por_patron(CAT.nanda, crosswalk_g, excepciones_g)
total_g = sum(len(v) for v in agrupado_g.values())
check("gordon: crosswalk reparte los 60 dx sin perder ni duplicar", 60, total_g)
check("gordon: excepción 00126 reclasificada", True,
      "Déficit de conocimientos" in agrupado_g.get("Percepción-manejo de la salud", []))
check("gordon: 00126 ya no está en Cognitivo-perceptual", False,
      "Déficit de conocimientos" in agrupado_g.get("Cognitivo-perceptual", []))



# ---------------------------------------------------------------
# Consolidación de hallazgos (engine/texto.py) — el gap real que
# encontramos: Gordon disparaba diagnósticos pero no llegaba al resumen
# narrativo ni a las alertas clínicas generales porque su lista nunca
# se mezclaba con hallazgos_seleccionados. Ahora la mezcla es una
# función testeada, no una concatenación inline en app.py.
# ---------------------------------------------------------------
from engine.texto import consolidar_hallazgos

check("consolidar: combina y deduplica", ["a", "b", "c"],
      consolidar_hallazgos(["a", "b"], ["b", "c"]))
check("consolidar: preserva orden de primera aparición", ["x", "y", "z"],
      consolidar_hallazgos(["x"], [], ["y", "x", "z"]))
check("consolidar: listas vacías o None no rompen", ["solo"],
      consolidar_hallazgos([], None, ["solo"], None))
check("consolidar: todo vacío -> vacío", [], consolidar_hallazgos([], [], []))

# El caso puntual del bug: hallazgos de Gordon deben terminar en la
# misma lista consolidada que ve generar_alertas_clinicas y el resumen.
hallazgos_gordon_test = hallazgos_desde_respuestas(patrones_g, {"peso_perdida": True})
consolidado_test = consolidar_hallazgos(["fiebre"], hallazgos_gordon_test)
check("consolidar: Gordon queda visible para alertas/resumen", True,
      "pérdida de peso" in consolidado_test)


# ---------------------------------------------------------------
# Reporte
# ---------------------------------------------------------------
print(f"\n{'='*60}")
print(f"Pruebas OK: {ok}")
print(f"Fallos:     {len(fallos)}")
print(f"{'='*60}")
if fallos:
    for nombre, esperado, obtenido in fallos:
        print(f"\nFALLO: {nombre}")
        print(f"  esperado: {esperado!r}")
        print(f"  obtenido: {obtenido!r}")
    sys.exit(1)
else:
    print("TODOS LOS GOLDEN TESTS PASARON")
    sys.exit(0)
