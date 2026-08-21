from engine.carga import cargar_catalogos


def test_catalogos_activos_tienen_vinculacion_completa() -> None:
    catalogos = cargar_catalogos("data")

    nombres_nanda = set(catalogos.nanda["nanda"])
    nanda_enlazados = set(catalogos.enlaces["nanda"])
    noc_enlazados = set(catalogos.enlaces["noc"])
    nic_enlazadas = set(catalogos.enlaces["nic"])

    assert nombres_nanda == nanda_enlazados
    assert nombres_nanda == set(catalogos.metas["nanda"])
    assert noc_enlazados <= set(catalogos.noc_indicadores["noc"])
    assert nic_enlazadas <= set(catalogos.nic_actividades["nic"])
    assert nic_enlazadas <= set(catalogos.fundamentos["nic"])


def test_catalogos_residuales_no_forman_parte_del_contrato_de_carga() -> None:
    catalogos = cargar_catalogos("data")

    assert not hasattr(catalogos, "noc")
    assert not hasattr(catalogos, "nic")
