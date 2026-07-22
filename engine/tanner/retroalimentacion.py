"""Retroalimentación determinista para la fase Noticing."""

from __future__ import annotations

from dataclasses import dataclass

from engine.tanner.casos import CasoTanner
from engine.tanner.modelos import ResultadoNoticing


@dataclass(frozen=True, slots=True)
class RetroalimentacionNoticing:
    """Retroalimentación estructurada y auditable de Noticing."""

    resumen: str
    fortalezas: tuple[str, ...]
    omisiones_criticas: tuple[str, ...]
    omisiones_esperadas: tuple[str, ...]
    selecciones_no_prioritarias: tuple[str, ...]
    advertencias: tuple[str, ...]
    prioridad_revision: str

    def como_texto(self) -> str:
        """Devuelve una representación legible sin alterar el contenido."""

        secciones = [self.resumen]

        _agregar_seccion(secciones, "Fortalezas", self.fortalezas)
        _agregar_seccion(
            secciones,
            "Omisiones críticas",
            self.omisiones_criticas,
        )
        _agregar_seccion(
            secciones,
            "Otros indicios esperados omitidos",
            self.omisiones_esperadas,
        )
        _agregar_seccion(
            secciones,
            "Datos no prioritarios seleccionados",
            self.selecciones_no_prioritarias,
        )
        _agregar_seccion(secciones, "Advertencias", self.advertencias)

        secciones.append(
            "Prioridad de revisión:\n"
            f"{self.prioridad_revision}"
        )

        return "\n\n".join(secciones)


def generar_retroalimentacion_noticing(
    caso: CasoTanner,
    resultado: ResultadoNoticing,
) -> RetroalimentacionNoticing:
    """Genera retroalimentación únicamente desde el contrato del caso."""

    por_id = {
        indicio.id: indicio
        for indicio in caso.indicios_noticing
    }

    total_esperados = sum(
        1
        for indicio in caso.indicios_noticing
        if indicio.esperado
    )
    total_reconocidos = len(resultado.reconocidos_esperados)

    resumen = (
        f"Se reconocieron {total_reconocidos} de "
        f"{total_esperados} indicios esperados."
    )

    fortalezas = tuple(
        _describir_indicio(por_id[identificador])
        for identificador in resultado.reconocidos_esperados
    )

    omisiones_criticas = tuple(
        _describir_indicio(por_id[identificador])
        for identificador in resultado.omisiones_criticas
    )

    ids_criticos = set(resultado.omisiones_criticas)
    omisiones_esperadas = tuple(
        _describir_indicio(por_id[identificador])
        for identificador in resultado.omitidos_esperados
        if identificador not in ids_criticos
    )

    selecciones_no_prioritarias = tuple(
        _describir_indicio(por_id[identificador])
        for identificador in resultado.seleccionados_no_prioritarios
    )

    advertencias = []

    if resultado.identificadores_desconocidos:
        advertencias.append(
            "Se recibieron identificadores inexistentes: "
            + ", ".join(resultado.identificadores_desconocidos)
            + "."
        )

    if resultado.seleccion_repetida:
        advertencias.append(
            "Se repitieron selecciones: "
            + ", ".join(resultado.seleccion_repetida)
            + "."
        )

    prioridad_revision = _determinar_prioridad_revision(resultado)

    return RetroalimentacionNoticing(
        resumen=resumen,
        fortalezas=fortalezas,
        omisiones_criticas=omisiones_criticas,
        omisiones_esperadas=omisiones_esperadas,
        selecciones_no_prioritarias=selecciones_no_prioritarias,
        advertencias=tuple(advertencias),
        prioridad_revision=prioridad_revision,
    )


def _describir_indicio(indicio) -> str:
    fundamento_visible = _humanizar_fundamento(indicio.fundamento)

    return (
        f"{indicio.texto}. "
        f"Fundamento: {fundamento_visible}."
    )


def _humanizar_fundamento(fundamento: str) -> str:
    """Convierte una clave técnica del YAML en texto legible."""

    texto = fundamento.replace("_", " ").strip()

    if not texto:
        return texto

    return texto[0].upper() + texto[1:]


def _determinar_prioridad_revision(
    resultado: ResultadoNoticing,
) -> str:
    if resultado.omisiones_criticas:
        return "Revisa primero los indicios críticos omitidos."

    if resultado.omitidos_esperados:
        return "Revisa los indicios esperados que no fueron seleccionados."

    if resultado.seleccionados_no_prioritarios:
        return (
            "Revisa la priorización: reconociste los indicios esperados, "
            "pero también seleccionaste datos no prioritarios."
        )

    if resultado.identificadores_desconocidos:
        return "Corrige los identificadores no reconocidos."

    if resultado.seleccion_repetida:
        return "Evita registrar el mismo indicio más de una vez."

    return "La selección reconoció los indicios esperados sin errores detectados."


def _agregar_seccion(
    secciones: list[str],
    titulo: str,
    elementos: tuple[str, ...],
) -> None:
    if not elementos:
        return

    cuerpo = "\n".join(
        f"- {elemento}"
        for elemento in elementos
    )
    secciones.append(f"{titulo}:\n{cuerpo}")
