"""Contexto de solo lectura autorizado para los agentes."""

from pathlib import Path


RAIZ_PROYECTO = Path(__file__).resolve().parent.parent

EXTENSIONES_PERMITIDAS = {
    ".py",
    ".yaml",
    ".yml",
    ".md",
    ".json",
}

DIRECTORIOS_PERMITIDOS = {
    "engine",
    "data",
    "tests",
    "scripts",
    "docs",
    "agents_kike_nnn",
}

ARCHIVOS_RAIZ_PERMITIDOS = {
    "app.py",
    "README.md",
    "pyproject.toml",
}


class ContextoNoAutorizado(ValueError):
    """La ruta solicitada no pertenece al contexto permitido."""


def validar_ruta(ruta_relativa: str) -> Path:
    ruta = Path(ruta_relativa)

    if ruta.is_absolute():
        raise ContextoNoAutorizado("No se permiten rutas absolutas.")

    if any(parte.startswith(".") for parte in ruta.parts):
        raise ContextoNoAutorizado("No se permiten archivos ocultos.")

    destino = (RAIZ_PROYECTO / ruta).resolve()

    try:
        destino.relative_to(RAIZ_PROYECTO)
    except ValueError as error:
        raise ContextoNoAutorizado(
            "La ruta sale del repositorio."
        ) from error

    if ruta.name in ARCHIVOS_RAIZ_PERMITIDOS:
        return destino

    if not ruta.parts or ruta.parts[0] not in DIRECTORIOS_PERMITIDOS:
        raise ContextoNoAutorizado(
            "El directorio no está autorizado."
        )

    if destino.suffix.lower() not in EXTENSIONES_PERMITIDAS:
        raise ContextoNoAutorizado(
            "El tipo de archivo no está autorizado."
        )

    return destino


def leer_archivo_autorizado(
    ruta_relativa: str,
    *,
    max_caracteres: int = 15_000,
) -> str:
    """Lee un archivo autorizado con un límite estricto."""

    destino = validar_ruta(ruta_relativa)

    if not destino.is_file():
        raise FileNotFoundError(
            f"No existe el archivo autorizado: {ruta_relativa}"
        )

    contenido = destino.read_text(
        encoding="utf-8",
        errors="replace",
    )

    if len(contenido) > max_caracteres:
        contenido = (
            contenido[:max_caracteres]
            + "\n\n[CONTENIDO TRUNCADO POR SEGURIDAD]"
        )

    return contenido


def construir_contexto(
    rutas: list[str],
    *,
    max_total: int = 60_000,
    max_por_archivo: int = 15_000,
) -> str:
    """Construye contexto explícito, limitado y trazable."""

    if not rutas:
        raise ValueError(
            "Debe proporcionarse al menos un archivo autorizado."
        )

    fragmentos: list[str] = []
    acumulado = 0
    rutas_vistas: set[str] = set()

    for ruta in rutas:
        if ruta in rutas_vistas:
            continue

        rutas_vistas.add(ruta)

        contenido = leer_archivo_autorizado(
            ruta,
            max_caracteres=max_por_archivo,
        )

        fragmento = (
            f"\n===== ARCHIVO AUTORIZADO: {ruta} =====\n"
            f"{contenido}\n"
        )

        if acumulado + len(fragmento) > max_total:
            espacio = max_total - acumulado

            if espacio > 0:
                fragmentos.append(
                    fragmento[:espacio]
                    + "\n[CONTEXTO TOTAL TRUNCADO]"
                )
            break

        fragmentos.append(fragmento)
        acumulado += len(fragmento)

    contexto = "".join(fragmentos).strip()

    if not contexto:
        raise ValueError("No fue posible construir contexto.")

    return contexto
