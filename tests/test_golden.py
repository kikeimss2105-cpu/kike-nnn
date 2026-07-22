from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_RUNNER = REPO_ROOT / "scripts" / "golden_runner.py"


def ejecutar_golden_runner() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GOLDEN_RUNNER)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_golden_runner_completo() -> None:
    resultado = ejecutar_golden_runner()
    salida = resultado.stdout + resultado.stderr

    assert resultado.returncode == 0, salida
    assert "Pruebas OK: 98" in salida
    assert "Fallos:     0" in salida
    assert "TODOS LOS GOLDEN TESTS PASARON" in salida


if __name__ == "__main__":
    resultado = ejecutar_golden_runner()
    print(resultado.stdout, end="")
    print(resultado.stderr, end="", file=sys.stderr)
    raise SystemExit(resultado.returncode)
