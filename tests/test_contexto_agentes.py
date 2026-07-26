import pytest

from agents_kike_nnn.contexto import (
    ContextoNoAutorizado,
    construir_contexto,
    leer_archivo_autorizado,
    validar_ruta,
)


def test_permite_archivo_controlado():
    ruta = validar_ruta("agents_kike_nnn/roles.py")

    assert ruta.name == "roles.py"
    assert ruta.is_file()


@pytest.mark.parametrize(
    "ruta",
    [
        ".env.agents",
        "../archivo.py",
        "/etc/passwd",
        "requirements-agents.txt",
        ".git/config",
    ],
)
def test_rechaza_rutas_no_autorizadas(ruta):
    with pytest.raises(ContextoNoAutorizado):
        validar_ruta(ruta)


def test_lee_archivo_con_limite():
    contenido = leer_archivo_autorizado(
        "agents_kike_nnn/roles.py",
        max_caracteres=100,
    )

    assert len(contenido) < 200
    assert "CONTENIDO TRUNCADO" in contenido


def test_construye_contexto_trazable():
    contexto = construir_contexto(
        [
            "agents_kike_nnn/roles.py",
            "agents_kike_nnn/comite.py",
        ],
        max_por_archivo=500,
        max_total=2_000,
    )

    assert "ARCHIVO AUTORIZADO" in contexto
    assert "agents_kike_nnn/roles.py" in contexto
    assert "agents_kike_nnn/comite.py" in contexto


def test_elimina_rutas_duplicadas():
    contexto = construir_contexto(
        [
            "agents_kike_nnn/roles.py",
            "agents_kike_nnn/roles.py",
        ],
        max_por_archivo=300,
    )

    encabezado = (
        "ARCHIVO AUTORIZADO: agents_kike_nnn/roles.py"
    )
    assert contexto.count(encabezado) == 1


def test_exige_al_menos_un_archivo():
    with pytest.raises(ValueError):
        construir_contexto([])
