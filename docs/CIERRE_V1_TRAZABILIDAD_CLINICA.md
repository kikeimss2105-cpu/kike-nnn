# Trazabilidad clínica para el cierre v1.0

## Estado del documento

Este inventario distingue implementación técnica de validación clínica. Una
prueba de software demuestra reproducibilidad, no corrección clínica.

Estados permitidos:

- `IMPLEMENTADO_NO_VALIDADO`: existe en código, pero el repositorio no contiene
  evidencia suficiente de revisión clínica humana por regla.
- `FUENTE_DECLARADA_PENDIENTE_REVISION`: el caso identifica una fuente, pero no
  existe constancia de revisión humana ni localización exacta de la regla.
- `BLOQUEO_CLINICO`: no puede cerrarse autónomamente sin fuente verificable y
  revisión humana.
- `VALIDADO_CLINICAMENTE`: reservado para una revisión humana documentada. En
  esta versión de trabajo ninguna regla alcanza todavía este estado.

## Matriz de componentes

| Área | Implementación actual | Evidencia presente | Estado de cierre |
|---|---|---|---|
| Motor NANDA | Coincidencia textual ponderada y umbral heredado | Golden de regresión; catálogos CSV | `BLOQUEO_CLINICO` para reinterpretar puntajes o umbrales |
| Enlaces NANDA–NOC–NIC | Enlaces, metas, indicadores, actividades y fundamentos | CSV consistentes y prueba de integridad | `IMPLEMENTADO_NO_VALIDADO` |
| Braden | Interpretación por puntaje | Código y Golden | `BLOQUEO_CLINICO` para validar umbrales y redacción |
| EVA | Interpretación por puntaje | Código y Golden | `BLOQUEO_CLINICO` para validar umbrales y redacción |
| Glasgow | Interpretación por puntaje | Código y Golden | `BLOQUEO_CLINICO` para validar umbrales y redacción |
| Caídas | Tamizaje propio por suma | Código y Golden | `BLOQUEO_CLINICO`: falta fuente y validación del instrumento |
| SpO2 y FR | Interpretaciones generales y por perfil | Código y Golden | `BLOQUEO_CLINICO`: falta fuente por población y contexto |
| Obstetricia | Cinco rutas educativas y alertas | Código, Golden y fuentes generales declaradas en OBS-HTA-001 | `BLOQUEO_CLINICO` por regla y texto de acción |
| Gordon | 4 de 11 patrones con 18 items | CSV, crosswalk, excepción y Golden | `BLOQUEO_CLINICO` para completar siete patrones y validar la excepción |
| Tanner Noticing | Comparación contra claves del caso | Contrato YAML y pruebas unitarias | `FUENTE_DECLARADA_PENDIENTE_REVISION` |
| Tanner Interpreting | Detección semántica acotada y filtrada | Contrato YAML y pruebas unitarias | `FUENTE_DECLARADA_PENDIENTE_REVISION` |
| Tanner Responding | Dominios preliminares sin motor | Borrador OBS-HTA-001 | `BLOQUEO_CLINICO` |
| Tanner Reflecting | Preguntas preliminares sin motor | Borrador OBS-HTA-001 | `BLOQUEO_CLINICO` para la clave; la captura técnica puede desarrollarse aislada |

## Fuentes declaradas actualmente

`data/casos/OBS-HTA-001.yaml` declara, sin localización de página o regla:

- IMSS-020, prevención, diagnóstico y tratamiento de la preeclampsia;
- IMSS-586, intervenciones de enfermería en trastornos hipertensivos;
- OMS, preeclampsia;
- ACOG, hipertensión y preeclampsia durante el embarazo.

La presencia de estos nombres no equivale a validación. Antes de retirar un
`BLOQUEO_CLINICO`, una persona revisora debe registrar versión/fecha, sección o
página, regla respaldada, decisión y nombre/rol de quien revisó.

## Bloqueos obligatorios antes de declarar v1.0 clínicamente revisada

1. Revisar todos los umbrales de `engine/interpretaciones.py`.
2. Revisar alertas de `engine/resumen.py`.
3. Revisar cada condición, nivel y acción de `engine/obstetrico.py`.
4. Revisar las transformaciones obstétricas duplicadas en `app.py`.
5. Validar el contenido de los seis CSV activos del plan NNN.
6. Validar `OBS-HTA-001`, incluyendo conceptos y relaciones de Interpreting.
7. Definir acciones esperadas e inseguras de Responding con fuente.
8. Definir la clave pedagógica de Reflecting con revisión docente.

## Regla de liberación

Mientras haya bloqueos clínicos P0, el sistema puede etiquetarse como
**candidato técnico educativo**, pero no como contenido clínico validado ni
como dispositivo médico. Ningún bloqueo se resuelve cambiando una prueba o
copiando una regla por analogía.
