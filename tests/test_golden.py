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
