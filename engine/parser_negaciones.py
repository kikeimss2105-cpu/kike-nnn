"""Adaptador determinista y conservador para texto clínico libre.

No es un parser clínico general. Reconoce únicamente construcciones cuyo
contrato fue aprobado para P0-NEGACIONES y marca como no confiables las
modalidades deliberadamente aplazadas.
"""

import re

from engine.evidencia import (
    ConfiabilidadEvidencia,
    EvidenciaClinica,
    FuenteEvidencia,
    PolaridadEvidencia,
    ResultadoParsing,
)
from engine.texto import normalizar_texto


NEGADORES_DIRECTOS = (
    "no se identifica",
    "no se observa",
    "no presenta",
    "no manifiesta",
    "ausencia de",
    "niega",
    "sin",
)

MARCADORES_NO_CONFIABLES = (
    "no refiere",
    "se descarta",
    "descarta",
    "posible",
    "probable",
    "historico",
    "previo",
    "resuelto",
)

# En estas construcciones el operador negativo recae sobre mejoría, control,
# respuesta o capacidad; no sobre el concepto clínico que aparece después.
EXCEPCIONES_POSITIVAS = (
    r"\bsin\s+mejoria\s+del?\b",
    r"\bsin\s+control\s+(?:de|del)\b",
    r"\bno\s+controla\b",
    r"\bsin\s+respuesta\s+al\s+tratamiento\b",
    r"\bno\s+disminuye\b",
    r"\bno\s+puede\s+dormir\s+por\b",
    r"\bno\s+tolera\s+alimentos\s+por\b",
    r"\bno\s+logra\s+expectorar\b",
)

_SEPARADOR_FUERTE = re.compile(r"[^.;\n]+")
_CONTRASTE = re.compile(r"\b(?:pero|sin\s+embargo)\b")
_REINICIO_POSITIVO = re.compile(r"(?<!no\s)\b(?:presenta|refiere)\b|\bcon\b")


def patron_termino(termino: str) -> re.Pattern:
    """Patrón Unicode con límites léxicos para términos y frases."""
    return re.compile(rf"(?<!\w){re.escape(normalizar_texto(termino))}(?!\w)")


def _menciones_no_superpuestas(texto: str, conceptos) -> list[tuple[int, int, str]]:
    candidatos = []
    conceptos_unicos = {normalizar_texto(c) for c in conceptos if normalizar_texto(c)}
    for concepto in conceptos_unicos:
        for match in patron_termino(concepto).finditer(texto):
            # "prematuro" dentro de "desprendimiento prematuro" no representa
            # por sí solo el concepto neonatal/gestacional catalogado.
            prefijo = texto[max(0, match.start() - 16):match.start()]
            if concepto == "prematuro" and prefijo.endswith("desprendimiento "):
                continue
            candidatos.append((match.start(), match.end(), concepto))

    candidatos.sort(key=lambda x: (-(x[1] - x[0]), x[0], x[2]))
    elegidos = []
    for candidato in candidatos:
        if any(candidato[0] < fin and candidato[1] > inicio for inicio, fin, _ in elegidos):
            continue
        elegidos.append(candidato)
    return sorted(elegidos)


def _ultimo_marcador(prefijo: str):
    marcadores = []
    for negador in NEGADORES_DIRECTOS:
        for match in patron_termino(negador).finditer(prefijo):
            marcadores.append((match.start(), "NEGADA"))
    for ambiguo in MARCADORES_NO_CONFIABLES:
        for match in patron_termino(ambiguo).finditer(prefijo):
            marcadores.append((match.start(), "NO_CONFIABLE"))
    for match in _REINICIO_POSITIVO.finditer(prefijo):
        marcadores.append((match.start(), "POSITIVA"))
    return max(marcadores, default=None, key=lambda x: x[0])


def _es_excepcion_positiva(texto_segmento: str, inicio_concepto: int) -> bool:
    prefijo = texto_segmento[:inicio_concepto]
    return any(re.search(patron, prefijo) for patron in EXCEPCIONES_POSITIVAS)


def parsear_texto_libre(texto, conceptos, *, origen="texto_libre") -> ResultadoParsing:
    """Extrae menciones catalogadas con polaridad, fuente y span original."""
    if texto is None or not str(texto).strip():
        return ResultadoParsing(())

    original = str(texto)
    normalizado = normalizar_texto(original)
    evidencias = []
    try:
        for clausula in _SEPARADOR_FUERTE.finditer(normalizado):
            texto_clausula = clausula.group(0)
            cortes = [0]
            cortes.extend(m.end() for m in _CONTRASTE.finditer(texto_clausula))
            cortes.append(len(texto_clausula))

            for indice in range(len(cortes) - 1):
                inicio_segmento, fin_segmento = cortes[indice], cortes[indice + 1]
                segmento = texto_clausula[inicio_segmento:fin_segmento]
                for inicio, fin, concepto in _menciones_no_superpuestas(segmento, conceptos):
                    marcador = _ultimo_marcador(segmento[:inicio])
                    polaridad = PolaridadEvidencia.POSITIVA
                    confiabilidad = ConfiabilidadEvidencia.CONFIABLE
                    if marcador and marcador[1] == "NEGADA":
                        polaridad = PolaridadEvidencia.NEGADA
                    elif marcador and marcador[1] == "NO_CONFIABLE":
                        polaridad = PolaridadEvidencia.NO_CONFIABLE
                        confiabilidad = ConfiabilidadEvidencia.NO_CONFIABLE
                    if any(
                        patron_termino(marcador_ambiguo).search(segmento)
                        for marcador_ambiguo in ("historico", "previo", "resuelto")
                    ):
                        polaridad = PolaridadEvidencia.NO_CONFIABLE
                        confiabilidad = ConfiabilidadEvidencia.NO_CONFIABLE
                    if _es_excepcion_positiva(segmento, inicio):
                        polaridad = PolaridadEvidencia.POSITIVA
                        confiabilidad = ConfiabilidadEvidencia.CONFIABLE

                    inicio_global = clausula.start() + inicio_segmento + inicio
                    fin_global = clausula.start() + inicio_segmento + fin
                    evidencias.append(EvidenciaClinica(
                        concepto=concepto,
                        texto_original=original[inicio_global:fin_global],
                        fuente=FuenteEvidencia.REFERIDO_TEXTO,
                        polaridad=polaridad,
                        confiabilidad=confiabilidad,
                        origen=origen,
                        inicio=inicio_global,
                        fin=fin_global,
                    ))
        return ResultadoParsing(tuple(evidencias))
    except Exception:
        return ResultadoParsing((), estado="PARSING_NO_CONFIABLE")


def conceptos_catalogo(nanda_df) -> list[str]:
    """Obtiene el vocabulario existente sin inventar conceptos clínicos."""
    from engine.texto import separar_lista

    conceptos = []
    for _, fila in nanda_df.iterrows():
        conceptos.append(str(fila.get("nanda", "")))
        for columna in ("caracteristicas", "relacionados", "asociados"):
            conceptos.extend(separar_lista(fila[columna]))
    return list(dict.fromkeys(conceptos))
