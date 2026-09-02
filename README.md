# KIKE-NNN v1.0.0-rc1

Sistema educativo de apoyo al juicio clínico en enfermería con enfoque
materno-neonatal. Sugiere, explica y permite argumentar; no emite diagnósticos
clínicos definitivos ni sustituye protocolos o revisión profesional.

## Estado real

Este commit es un **candidato técnico**, no la liberación clínica final v1.0.0.
Los bloqueos pendientes están documentados en
`docs/CIERRE_V1_TRAZABILIDAD_CLINICA.md`.

Módulos integrados:

- sugerencias educativas NANDA con vínculos NOC/NIC;
- metas, indicadores, actividades y fundamentos declarativos;
- valoración general y piloto Gordon de 4/11 patrones;
- cinco rutas obstétricas educativas;
- APGAR, Silverman-Andersen y Capurro A/B deterministas;
- análisis docente basado en reglas explícitas;
- exportación a Excel y Word;
- Tanner Noticing e Interpreting aislados y probados.

Tanner Responding cuenta únicamente con dominios no farmacológicos validados
con límites; su motor de acciones y la farmacología permanecen bloqueados.
Reflecting tiene validación pedagógica limitada, mientras que la puntuación y
la máquina de estados continúan bloqueadas. Un fallo del LLM se informa como
fallo técnico y nunca se convierte en una valoración negativa del estudiante.

## Instalación de desarrollo

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

En Windows PowerShell, active el entorno con `.venv\Scripts\Activate.ps1`.

## Validación obligatoria

```bash
python3 scripts/golden_runner.py
python -m pytest -q
```

Ejecute ambos comandos dentro del entorno virtual activado.

## Datos activos

El flujo NNN consume `nanda.csv`, `enlaces.csv`, `noc_indicadores.csv`,
`nic_actividades.csv`, `fundamentos.csv` y `metas.csv`. `noc.csv` y `nic.csv`
son archivos residuales y no alimentan el motor.

## Seguridad y alcance

- Uso exclusivamente educativo.
- No es un dispositivo médico.
- No prescribe ni decide tratamientos.
- Ningún dato ausente se completa como cero.
- La IA no puede modificar las claves clínicas de los casos.
- No introduzca datos identificables de pacientes en pruebas o servicios LLM.
