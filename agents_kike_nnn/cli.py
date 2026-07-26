"""Interfaz de terminal para el comité consultivo KIKE-NNN."""

import argparse

from agents_kike_nnn.comite import ComiteKikeNNN
from agents_kike_nnn.contexto import (
    ContextoNoAutorizado,
    construir_contexto,
)


def leer_solicitud_multilinea() -> str:
    print(
        "\nEscribe la solicitud para el comité."
        "\nTermina escribiendo FIN en una línea independiente.\n"
    )

    lineas: list[str] = []

    while True:
        try:
            linea = input()
        except EOFError:
            break

        if linea.strip().upper() == "FIN":
            break

        lineas.append(linea)

    solicitud = "\n".join(lineas).strip()

    if not solicitud:
        raise ValueError("La solicitud está vacía.")

    return solicitud


def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Comité consultivo y de solo lectura para KIKE-NNN."
        )
    )

    parser.add_argument(
        "--archivo",
        action="append",
        required=True,
        help=(
            "Archivo autorizado para el contexto. "
            "Puede repetirse varias veces."
        ),
    )

    parser.add_argument(
        "--solicitud",
        help=(
            "Solicitud breve. Si se omite, se habilita entrada "
            "multilínea terminada con FIN."
        ),
    )

    return parser


def imprimir_informe(
    titulo: str,
    resultado,
) -> None:
    print(f"\n{'=' * 70}")
    print(titulo)
    print(f"Modelo: {resultado.modelo_utilizado}")
    print(f"Correcto: {resultado.correcto}")
    print(
        "Duración:",
        round(resultado.duracion_segundos, 2),
        "segundos",
    )

    if resultado.correcto:
        print("-" * 70)
        print(resultado.contenido)
    else:
        print("Error:", resultado.tipo_error)
        print("Detalle:", resultado.detalle_error)


def main() -> int:
    argumentos = crear_parser().parse_args()

    try:
        solicitud = (
            argumentos.solicitud.strip()
            if argumentos.solicitud
            else leer_solicitud_multilinea()
        )

        contexto = construir_contexto(argumentos.archivo)

    except (
        ValueError,
        FileNotFoundError,
        ContextoNoAutorizado,
    ) as error:
        print(f"\nENTRADA_RECHAZADA: {error}")
        return 2

    print("\nContexto autorizado:")
    for archivo in argumentos.archivo:
        print(f"- {archivo}")

    print("\nEl comité está trabajando...")
    expediente = ComiteKikeNNN().evaluar(
        solicitud=solicitud,
        contexto_controlado=contexto,
    )

    imprimir_informe(
        "INFORME DEL ARQUITECTO",
        expediente.arquitectura,
    )

    if expediente.programacion is not None:
        imprimir_informe(
            "PROPUESTA DEL PROGRAMADOR",
            expediente.programacion,
        )

    if expediente.auditoria is not None:
        imprimir_informe(
            "AUDITORÍA ADVERSARIAL",
            expediente.auditoria,
        )

    print(f"\nESTADO DEL COMITÉ: {expediente.estado}")
    print(
        "Ningún archivo fue modificado por los agentes."
    )

    return 0 if expediente.completo else 3


if __name__ == "__main__":
    raise SystemExit(main())
