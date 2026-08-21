from engine.tanner.interpreting import describir_error_publico


def test_error_publico_no_expone_mensaje_sensible() -> None:
    error = RuntimeError("https://proveedor.example?key=secreto-no-mostrar")

    detalle = describir_error_publico(error)

    assert detalle == "Fallo técnico del proveedor (RuntimeError)."
    assert "secreto-no-mostrar" not in detalle
    assert "https://" not in detalle
