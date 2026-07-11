"""
Capa de intake por Patrones Funcionales de Gordon.

Principio de diseño: Gordon organiza la RECOLECCIÓN de datos (cómo se
pregunta), NANDA clasifica el DIAGNÓSTICO (qué se concluye). No son
intercambiables — este módulo NO reemplaza engine/motor.py ni
engine/obstetrico.py, solo les alimenta datos con una estructura distinta
a la del formulario libre actual.

Pipeline resultante:
    Gordon (este módulo) -> hallazgos (list[str] / texto_clinico)
                          -> engine.motor.buscar_diagnosticos (sin cambios)
                          -> engine.obstetrico.evaluar_rutas_obstetricas (sin cambios)

Ver data/crosswalk_gordon_nanda.csv para la correspondencia patrón->dominio
NANDA con los huecos declarados explícitamente (Seguridad/Protección y
Crecimiento/Desarrollo no tienen patrón de origen limpio en Gordon).
"""
from dataclasses import dataclass, field
import pandas as pd

# Orden y nombres oficiales de los 11 patrones de Gordon.
PATRONES = [
    ("percepcion_manejo_salud", "1. Percepción-manejo de la salud"),
    ("nutricional_metabolico", "2. Nutricional-metabólico"),
    ("eliminacion", "3. Eliminación"),
    ("actividad_ejercicio", "4. Actividad-ejercicio"),
    ("sueno_descanso", "5. Sueño-descanso"),
    ("cognitivo_perceptual", "6. Cognitivo-perceptual"),
    ("autopercepcion", "7. Autopercepción-autoconcepto"),
    ("rol_relaciones", "8. Rol-relaciones"),
    ("sexualidad_reproduccion", "9. Sexualidad-reproducción"),
    ("afrontamiento_tolerancia_estres", "10. Afrontamiento-tolerancia al estrés"),
    ("valores_creencias", "11. Valores-creencias"),
]


@dataclass
class ItemGordon:
    item_id: str
    pregunta: str
    tipo: str
    hallazgo_texto: str


@dataclass
class PatronGordon:
    patron_id: str
    nombre: str
    items: list = field(default_factory=list)
    estado: str = "pendiente_criterio_clinico"  # "listo" si tiene items reales


def cargar_patrones_gordon(data_dir: str = "data") -> list[PatronGordon]:
    """Carga data/gordon_items.csv y arma los 11 patrones en orden fijo.
    Los patrones sin items reales quedan con estado 'pendiente_criterio_clinico'
    y lista de items vacía — no se inventan preguntas clínicas aquí."""
    items_df = pd.read_csv(f"{data_dir}/gordon_items.csv", dtype=str)

    patrones = []
    for patron_id, nombre in PATRONES:
        filas = items_df[items_df["patron_id"] == patron_id]
        filas_reales = filas[filas["estado"] == "listo"]

        items = [
            ItemGordon(
                item_id=row["item_id"],
                pregunta=row["pregunta"],
                tipo=row["tipo"],
                hallazgo_texto=row["hallazgo_texto"],
            )
            for _, row in filas_reales.iterrows()
        ]
        estado = "listo" if items else "pendiente_criterio_clinico"
        patrones.append(PatronGordon(patron_id=patron_id, nombre=nombre, items=items, estado=estado))

    return patrones


def hallazgos_desde_respuestas(patrones: list[PatronGordon], respuestas: dict) -> list[str]:
    """Convierte respuestas del intake Gordon {item_id: bool} al mismo
    vocabulario de hallazgos que ya consume engine.motor.buscar_diagnosticos
    y engine.obstetrico.evaluar_rutas_obstetricas. No requiere ningún cambio
    en esas funciones."""
    hallazgos = []
    for patron in patrones:
        for item in patron.items:
            if respuestas.get(item.item_id):
                hallazgos.append(item.hallazgo_texto)
    return hallazgos


def cargar_crosswalk(data_dir: str = "data") -> pd.DataFrame:
    """Carga el crosswalk Gordon->NANDA documentado, incluyendo los huecos
    declarados (SIN_PATRON_GORDON). Uso: anexo metodológico de tesis y
    para agrupar el catálogo NANDA por patrón en la UI."""
    return pd.read_csv(f"{data_dir}/crosswalk_gordon_nanda.csv")


def cargar_excepciones(data_dir: str = "data") -> pd.DataFrame:
    """Carga reclasificaciones clínicas deliberadas que se apartan del
    dominio NANDA original de un diagnóstico específico (ej. 00126, que
    NANDA ubica en Percepción/Cognición pero que clínicamente corresponde
    a Percepción-manejo de la salud de Gordon). Cada excepción debe traer
    su propia justificación explícita — no son ajustes silenciosos."""
    try:
        return pd.read_csv(f"{data_dir}/crosswalk_excepciones.csv", dtype={"codigo_nanda": str})
    except FileNotFoundError:
        return pd.DataFrame(columns=["codigo_nanda", "nanda", "dominio_nanda_original",
                                      "patron_gordon_asignado", "justificacion"])


def agrupar_nanda_por_patron(nanda_df: pd.DataFrame, crosswalk_df: pd.DataFrame,
                              excepciones_df: pd.DataFrame = None) -> dict:
    """Agrupa los diagnósticos NANDA existentes según el patrón Gordon de
    origen de su dominio (y clase, cuando un dominio se reparte entre dos
    patrones — ej. Actividad/Reposo se divide entre Actividad-ejercicio y
    Sueño-descanso según la clase NANDA). Los dominios sin patrón
    (SIN_PATRON_GORDON) quedan agrupados aparte, explícitamente.

    Las excepciones (excepciones_df) tienen prioridad sobre la regla
    dominio+clase: son reclasificaciones clínicas deliberadas para un
    código NANDA específico, cada una con su propia justificación
    documentada en data/crosswalk_excepciones.csv."""
    excepcion_por_codigo = {}
    if excepciones_df is not None and not excepciones_df.empty:
        for _, fila in excepciones_df.iterrows():
            excepcion_por_codigo[fila["codigo_nanda"]] = fila["patron_gordon_asignado"]

    reglas = []
    for _, fila in crosswalk_df.iterrows():
        if fila["patron_gordon"] == "SIN_PATRON_GORDON" or not fila["dominio_nanda"] or pd.isna(fila["dominio_nanda"]):
            continue
        clase = fila["clase_nanda"] if pd.notna(fila.get("clase_nanda")) and fila.get("clase_nanda") else None
        reglas.append((fila["dominio_nanda"], clase, fila["patron_gordon"]))

    def resolver_patron(codigo, dominio, clase):
        if codigo in excepcion_por_codigo:
            return excepcion_por_codigo[codigo]
        for d, c, patron in reglas:
            if d == dominio and c == clase:
                return patron
        for d, c, patron in reglas:
            if d == dominio and c is None:
                return patron
        return None

    resultado = {}
    sin_patron = []
    for _, fila in nanda_df.iterrows():
        patron = resolver_patron(fila["codigo"], fila["dominio"], fila["clase"])
        if patron:
            resultado.setdefault(patron, []).append(fila["nanda"])
        else:
            sin_patron.append(fila["nanda"])

    if sin_patron:
        resultado["Sin patrón Gordon de origen (dominio NANDA sin correspondencia)"] = sin_patron

    return resultado
