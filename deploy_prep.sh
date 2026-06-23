#!/bin/bash
# =============================================================
# KIKE-NNN — Script de preparación para deploy en Streamlit Cloud
# Ejecutar desde: ~/ProyectosIA/generador_nnn_v18_1_ajuste_fino_obstetrico_estable/
# Uso: bash deploy_prep.sh
# =============================================================

set -e  # Detener si cualquier comando falla

REPO_DIR="$HOME/kike-nnn-deploy"
SOURCE_DIR="$(pwd)"

echo ""
echo "================================================="
echo "  KIKE-NNN v18.1 — Preparación para deploy"
echo "================================================="
echo ""

# 1. Crear carpeta del repo
echo "[1/5] Creando carpeta del repositorio..."
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR/utils" "$REPO_DIR/data" "$REPO_DIR/.streamlit"

# 2. Copiar archivos esenciales
echo "[2/5] Copiando archivos de la app..."
cp "$SOURCE_DIR/app.py" "$REPO_DIR/"
cp "$SOURCE_DIR/utils/exportadores.py" "$REPO_DIR/utils/"
touch "$REPO_DIR/utils/__init__.py"

# Copiar todos los CSV de data/
cp "$SOURCE_DIR/data/"*.csv "$REPO_DIR/data/"
echo "      CSVs copiados: $(ls "$REPO_DIR/data/"*.csv | wc -l) archivos"

# 3. Crear archivos de configuración
echo "[3/5] Creando archivos de configuración..."

cat > "$REPO_DIR/requirements.txt" << 'REQ'
streamlit>=1.35.0
pandas>=2.0.0
openpyxl>=3.1.0
python-docx>=1.0.0
REQ

cat > "$REPO_DIR/.streamlit/config.toml" << 'CFG'
[browser]
gatherUsageStats = false

[theme]
base = "light"

[server]
maxUploadSize = 5
CFG

cat > "$REPO_DIR/.gitignore" << 'GIT'
venv/
.venv/
__pycache__/
*.py[cod]
migrate.py
migrations/
*.zip
ledger.json
.DS_Store
GIT

# 4. Verificar que app.py tiene el disclaimer bloqueante
echo "[4/5] Verificando app.py..."
if grep -q "st.stop()" "$REPO_DIR/app.py"; then
    echo "      ✓ Disclaimer bloqueante presente"
else
    echo "      ✗ ADVERTENCIA: st.stop() no encontrado en app.py"
    echo "        El app.py del repo debe ser la versión modificada, no la original."
fi

python3 -c "
import ast
with open('$REPO_DIR/app.py') as f: src = f.read()
ast.parse(src)
print('      ✓ app.py compila sin errores de sintaxis')
"

# 5. Resultado
echo "[5/5] Estructura final del repositorio:"
find "$REPO_DIR" -not -path '*/__pycache__/*' | sort

echo ""
echo "================================================="
echo "  Listo. Ahora sigue estos pasos:"
echo "================================================="
echo ""
echo "  PASO A — Inicializar git:"
echo "  cd $REPO_DIR"
echo "  git init"
echo "  git add ."
echo "  git commit -m 'feat: KIKE-NNN v18.1 deploy inicial'"
echo ""
echo "  PASO B — Crear repo en GitHub:"
echo "  1. Ve a https://github.com/new"
echo "  2. Nombre: kike-nnn"
echo "  3. Privado (Private) ← recomendado"
echo "  4. NO marques 'Add README' ni ninguna opción extra"
echo "  5. Crea el repo y copia la URL que aparece"
echo ""
echo "  PASO C — Subir código:"
echo "  git remote add origin https://github.com/TU-USUARIO/kike-nnn.git"
echo "  git push -u origin main"
echo ""
echo "  PASO D — Deploy en Streamlit Cloud:"
echo "  1. Ve a https://share.streamlit.io"
echo "  2. New app"
echo "  3. Selecciona el repo kike-nnn"
echo "  4. Branch: main"
echo "  5. Main file path: app.py"
echo "  6. App URL: kike-nnn (o el nombre que quieras)"
echo "  7. Deploy!"
echo ""
echo "  La app estará lista en 2-3 minutos."
echo "================================================="
