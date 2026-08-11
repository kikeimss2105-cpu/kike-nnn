# Contexto permanente de KIKE-NNN

## Propósito

KIKE-NNN es un sistema educativo de apoyo al juicio clínico en enfermería. No es un generador automático de PAE ni emite diagnósticos clínicos definitivos.

Su principio rector es: la herramienta puede sugerir, cuestionar y retroalimentar; la decisión clínica debe permanecer en el estudiante o profesional. Su uso no sustituye el juicio profesional, los protocolos institucionales ni la revisión clínica humana.

## Filosofía de trabajo

- Enseñar antes que automatizar.
- Explicabilidad antes que magia.
- Seguridad antes que comodidad.
- La IA no define la verdad clínica.
- Toda regla clínica requiere fuente.
- Todo cambio debe ser auditable.
- Un fallo técnico nunca debe convertirse en una mala evaluación del alumno.

Ante una duda clínica, no inventar ni completar por analogía: detener la implementación y reportar la duda para revisión clínica.

## Arquitectura actual

- `app.py`: interfaz Streamlit y orquestación actual de la aplicación. Es una zona de alto impacto; no modificar sin una tarea explícita.
- `engine/`: lógica de negocio separada de la interfaz. Incluye carga de catálogos, normalización de texto, búsqueda de diagnósticos, interpretaciones, rutas obstétricas, plan, resumen y análisis docente.
- `engine/tanner/`: módulo pedagógico aislado para el Modelo de Juicio Clínico de Tanner. No está integrado directamente en `app.py`.
- `engine/gordon.py`: intake mediante los 11 Patrones Funcionales de Gordon. Gordon organiza la recolección de datos; NANDA clasifica diagnósticos. No son intercambiables. Convierte respuestas a hallazgos para los motores existentes y mantiene crosswalks y excepciones explícitas.
- `data/`: catálogos CSV, crosswalks y casos YAML. Es la fuente de datos del sistema y no debe alterarse sin contrato, evidencia y revisión correspondiente.
- `data/casos/`: casos educativos declarativos en YAML. Sus claves, indicios y conceptos constituyen el contrato del caso.
- `tests/`: protección de regresiones del motor, incluido el corredor Golden y pruebas unitarias de Tanner.
- `utils/`: utilidades, entre ellas exportación a Excel y Word.
- `scripts/golden_runner.py`: ejecuta la referencia Golden del comportamiento del motor.

## Flujo NANDA–NOC–NIC actual

`engine.carga.cargar_catalogos()` carga `nanda.csv`, `enlaces.csv`, `noc_indicadores.csv`, `nic_actividades.csv`, `fundamentos.csv` y `metas.csv`.

`engine.motor.buscar_diagnosticos()` normaliza los hallazgos, busca coincidencias de características definitorias, relacionados y asociados en el catálogo NANDA, y devuelve sugerencias enlazadas a NOC, NIC y prioridad desde `enlaces.csv`. Las sugerencias conservan la nota de que requieren validación clínica.

`engine.plan.enriquecer_plan()` agrega meta esperada, indicadores NOC, actividades NIC y fundamentos desde los catálogos cargados. No inventar campos ni afirmar que `data/noc.csv` o `data/nic.csv` alimentan este flujo: actualmente son archivos residuales no utilizados.

Los puntajes y niveles existentes pertenecen a la lógica heredada y probada del motor educativo; no deben reinterpretarse como una calificación clínica nueva ni modificarse sin fuente, contrato y pruebas Golden actualizadas por una razón válida.

## Tanner: contrato y límites

Tanner se desarrolla como módulo pedagógico aislado y auditable.

- **Noticing** es determinista: el caso YAML declara los indicios, sus identificadores, categorías, si son esperados y su fundamento. La selección se compara contra esas claves; no asigna calificación numérica.
- **Interpreting** admite comprensión semántica de texto libre mediante un LLM acotado. El LLM solo puede identificar conceptos y relaciones que ya estén definidos en el YAML del caso; cualquier salida ajena se filtra.
- La clave clínica procede del caso YAML, nunca del LLM.
- La retroalimentación final de Noticing e Interpreting se construye de forma determinista desde el contrato del caso y el resultado filtrado; debe permanecer reproducible y auditable.
- Si el cliente LLM, la API o el formato de respuesta falla, la evaluación se marca como no confiable y se informa el fallo. No convertirlo en una omisión, juicio ni resultado negativo del estudiante.
- No introducir puntuaciones arbitrarias, reglas farmacológicas ni decisiones clínicas no definidas en el contrato del caso.

El contrato de `docs/casos/OBS-HTA-001_CONTRATO.md` es un borrador clínico y pedagógico. Cualquier ampliación debe preservar que el caso es exclusivamente educativo y esperar fuente y revisión humana para intervenciones farmacológicas u otros contenidos clínicos.

## Enfoque materno-neonatal

KIKE-NNN está evolucionando hacia un enfoque materno-neonatal para uso educativo institucional. La funcionalidad obstétrica existente y los casos educativos deben tratarse como apoyo a la enseñanza, no como sustitutos de protocolos o atención clínica.

No documentar ni implementar `NEO-001` como existente a menos que esté presente explícitamente en la rama de trabajo.

## Seguridad clínica y uso de LLM

Nunca inventar:

- fórmulas, constantes o umbrales;
- códigos NANDA, NOC o NIC;
- intervenciones;
- fuentes o fundamentos clínicos.

El uso de LLM está permitido para comprensión semántica, apoyo de implementación y clasificación restringida por contratos definidos. No está permitido para inventar verdad clínica, cambiar claves de caso, generar puntuaciones arbitrarias ni transformar una falla de API en una valoración negativa del alumno.

## Pruebas y criterio de terminado

Los comandos de validación obligatorios actuales son:

```bash
python3 scripts/golden_runner.py
python -m pytest -q
