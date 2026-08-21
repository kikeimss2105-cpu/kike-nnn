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
| Tanner Noticing | Comparación contra claves del caso | Contrato YAML, decisión humana P0 y pruebas unitarias | `VALIDADO_PARCIALMENTE`: R03 y R05 corregidas |
| Tanner Interpreting | Detección semántica acotada y filtrada | Contrato YAML, decisión humana P0 y pruebas unitarias | `VALIDADO_CON_LIMITES` para R11 |
| Tanner Responding | Dominios no farmacológicos declarados, sin motor de acciones | Decisión humana P0 sobre OBS-HTA-001 | `VALIDADO_CON_LIMITES`: solo dominios no farmacológicos; farmacología bloqueada |
| Tanner Reflecting | Clave propuesta de reflexión | Decisión humana P0; fundamento Tanner 2006 | `VALIDADO_PEDAGOGICAMENTE`; puntuación y estados bloqueados |

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
6. Mantener bloqueada la farmacología de `OBS-HTA-001` hasta contar con fuente,
   protocolo y revisión clínica.
7. Definir acciones esperadas e inseguras de Responding sin ampliar el alcance
   farmacológico validado.
8. Mantener sin puntuación y sin máquina de estados hasta validación específica.

## Decisión humana P0 sobre OBS-HTA-001

- Validadas: R01, R02, R04, R06, R07, R08, R09, R10, R12, R13, R14,
  R15, R16, R17, R18, R21 y R24.
- Validadas con límites: R11 y R19.
- Corregidas: R03 (`alteracion_visual`) y R05 (`inquietud` no esperada).
- Bloqueadas: R20 farmacología, R22 puntuación numérica y R23 máquina de
  estados.

## Regla de liberación

Mientras haya bloqueos clínicos P0, el sistema puede etiquetarse como
**candidato técnico educativo**, pero no como contenido clínico validado ni
como dispositivo médico. Ningún bloqueo se resuelve cambiando una prueba o
copiando una regla por analogía.
