#!/bin/bash

set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEST_DIR="$HOME/kike-nnn-deploy"
EXECUTE=false

usage() {
    cat <<'USAGE'
Uso:
  bash deploy_prep.sh [--dest RUTA]
  bash deploy_prep.sh --execute [--dest RUTA]

Sin --execute, el script únicamente muestra el plan y no escribe archivos.

Opciones:
  --execute       Ejecuta la preparación del destino.
  --dest RUTA     Selecciona un destino nuevo y explícito.
  -h, --help      Muestra esta ayuda.
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --execute)
            EXECUTE=true
            shift
            ;;
        --dest)
            if [[ $# -lt 2 || -z "$2" ]]; then
                echo "ERROR: --dest requiere una ruta." >&2
                exit 2
            fi
            DEST_DIR="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: argumento desconocido: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

REQUIRED_SOURCES=(
    "app.py"
    "requirements.txt"
    ".streamlit/config.toml"
    "engine/__init__.py"
    "engine/carga.py"
    "engine/criterios.py"
    "engine/docente.py"
    "engine/gordon.py"
    "engine/interpretaciones.py"
    "engine/motor.py"
    "engine/obstetrico.py"
    "engine/plan.py"
    "engine/resumen.py"
    "engine/texto.py"
    "utils/__init__.py"
    "utils/exportadores.py"
)

for relative_path in "${REQUIRED_SOURCES[@]}"; do
    if [[ ! -f "$SOURCE_DIR/$relative_path" ]]; then
        echo "ERROR: falta el archivo requerido: $SOURCE_DIR/$relative_path" >&2
        exit 1
    fi
done

if [[ ! -d "$SOURCE_DIR/data" ]]; then
    echo "ERROR: falta el directorio requerido: $SOURCE_DIR/data" >&2
    exit 1
fi

mapfile -d '' SOURCE_CSV_FILES < <(
    find "$SOURCE_DIR/data" -type f -name '*.csv' -print0
)
SOURCE_CSV_COUNT="${#SOURCE_CSV_FILES[@]}"

if [[ "$SOURCE_CSV_COUNT" -eq 0 ]]; then
    echo "ERROR: data/ no contiene ningún archivo CSV." >&2
    exit 1
fi

if [[ -e "$DEST_DIR" ]]; then
    echo "ERROR: el destino ya existe y no será modificado: $DEST_DIR" >&2
    exit 1
fi

echo "================================================="
echo "  KIKE-NNN v19 — Preparación segura para deploy"
echo "================================================="
echo "Origen:      $SOURCE_DIR"
echo "Destino:     $DEST_DIR"
echo "CSV origen:  $SOURCE_CSV_COUNT"
echo
echo "Plan:"
echo "  1. Crear un destino nuevo."
echo "  2. Copiar app.py."
echo "  3. Copiar engine/, utils/ y data/ sin cachés ni bytecode."
echo "  4. Copiar .streamlit/config.toml."
echo "  5. Copiar requirements.txt."
echo "  6. Validar módulos, exclusiones y cantidad de CSV copiados."
echo

if [[ "$EXECUTE" != true ]]; then
    echo "Modo seguro: no se escribió ningún archivo."
    echo "Para ejecutar este plan, usa --execute."
    exit 0
fi

echo "[1/6] Creando destino nuevo..."
mkdir -- "$DEST_DIR"

echo "[2/6] Copiando app.py..."
cp -- "$SOURCE_DIR/app.py" "$DEST_DIR/"

echo "[3/6] Copiando módulos y datos sin cachés ni bytecode..."
tar \
    --exclude='*/__pycache__' \
    --exclude='*/__pycache__/*' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    -C "$SOURCE_DIR" \
    -cf - engine utils data |
    tar -C "$DEST_DIR" -xf -

echo "[4/6] Copiando configuración canónica..."
mkdir -- "$DEST_DIR/.streamlit"
cp -- "$SOURCE_DIR/.streamlit/config.toml" "$DEST_DIR/.streamlit/"

echo "[5/6] Copiando requirements.txt..."
cp -- "$SOURCE_DIR/requirements.txt" "$DEST_DIR/"

echo "[6/6] Validando contenido copiado..."
for relative_path in "${REQUIRED_SOURCES[@]}"; do
    if [[ ! -f "$DEST_DIR/$relative_path" ]]; then
        echo "ERROR: no se copió el archivo requerido: $DEST_DIR/$relative_path" >&2
        exit 1
    fi
done

if [[ ! -d "$DEST_DIR/data" ]]; then
    echo "ERROR: no se copió el directorio de datos." >&2
    exit 1
fi

mapfile -d '' DEST_CSV_FILES < <(
    find "$DEST_DIR/data" -type f -name '*.csv' -print0
)
DEST_CSV_COUNT="${#DEST_CSV_FILES[@]}"

if [[ "$DEST_CSV_COUNT" -ne "$SOURCE_CSV_COUNT" ]]; then
    echo "ERROR: la cantidad de CSV no coincide." >&2
    echo "Origen: $SOURCE_CSV_COUNT; destino: $DEST_CSV_COUNT" >&2
    exit 1
fi

EXCLUDED_ARTIFACT="$(
    find "$DEST_DIR/engine" "$DEST_DIR/utils" "$DEST_DIR/data" \
        \( -type d -name '__pycache__' \
        -o -type f -name '*.pyc' \
        -o -type f -name '*.pyo' \) \
        -print -quit
)"

if [[ -n "$EXCLUDED_ARTIFACT" ]]; then
    echo "ERROR: se copió un artefacto excluido: $EXCLUDED_ARTIFACT" >&2
    exit 1
fi

echo
echo "Preparación completada correctamente."
echo "Destino:      $DEST_DIR"
echo "CSV copiados: $DEST_CSV_COUNT"
echo "No se instalaron dependencias ni se ejecutó Streamlit."
