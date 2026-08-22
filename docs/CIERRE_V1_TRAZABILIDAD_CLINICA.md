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
| Obstetricia | Cinco rutas educativas y alertas saneadas para no fabricar diagnósticos ni datos ausentes | Código, decisión humana P0, Golden y pruebas de frontera | `IMPLEMENTADO_NO_VALIDADO`: fuentes mapeadas por grupo, pendientes de localización y revisión documental |
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

## Mapeo P0 de fuentes para reglas obstétricas

Este mapeo registra la asignación indicada por la decisión humana
`P0-OBSTETRICIA`. No afirma que la fuente haya sido cotejada ni que la regla
esté clínicamente validada. Faltan versión, fecha, sección/página y constancia
de revisión para cada referencia.

| Grupo de reglas | Contenido implementado | Fuente indicada | Estado |
|---|---|---|---|
| P0-OBS-R001–R005, R015–R025, R045–R052, R063–R064 y R069–R073 | PA, signos de alarma y evaluación de trastorno hipertensivo | IMSS-058; IMSS-586; ACOG | `FUENTE_DECLARADA_PENDIENTE_REVISION` |
| P0-OBS-R007–R009 y R026–R032 | Sospecha de ruptura de membranas y posible riesgo infeccioso | IMSS-321-11 | `FUENTE_DECLARADA_PENDIENTE_REVISION` |
| P0-OBS-R011, R035, R038 y R059 | Contracciones antes de término con edad gestacional menor de 37 semanas | IMSS-063-08 | `FUENTE_DECLARADA_PENDIENTE_REVISION` |
| P0-OBS-R006, R033–R036, R053 y R066 | Sangrado vaginal y ruta de valoración de sangrado obstétrico | IMSS-162-09, *Diagnóstico y tratamiento del choque hemorrágico en obstetricia*, actualización 2017 | `VALIDADO_CON_LIMITES` |
| P0-OBS-R012–R014, R040–R044, R054–R062 y R065–R068 | Control prenatal, alarmas generales y valoración materno-fetal | IMSS-028; IMSS-436, cuando corresponda | `FUENTE_DECLARADA_PENDIENTE_REVISION` |

La referencia histórica IMSS-020 permanece declarada en `OBS-HTA-001`, pero
no se usa para sustituir ni inferir el identificador IMSS-058 indicado en la
decisión P0. La discrepancia bibliográfica requiere revisión humana.

### Decisión humana P0-HEMORRAGIA

- **Institución:** Instituto Mexicano del Seguro Social.
- **Clave:** IMSS-162-09.
- **Título:** *Diagnóstico y tratamiento del choque hemorrágico en obstetricia*.
- **Actualización:** 2017.
- **Evidencia relevante:** la clasificación del choque considera la cantidad
  estimada de sangrado y las manifestaciones clínicas. Esta guía no se usa para
  afirmar que cualquier sangrado aislado equivale a hemorragia o choque.
- `sangrado vaginal` permanece como dato observado, sin inferir por sí solo
  gravedad, etiología, choque ni compromiso fetal.
- Los términos textuales generales `hemorragia` y `sangrado obstétrico` no se
  transforman automáticamente en localización vaginal.
- La ruta se denomina `Sangrado obstétrico / requiere valoración` y no expresa
  un diagnóstico ni una clasificación de gravedad clínica.
- Las etiquetas NANDA generadas por una ruta no se reutilizan como evidencia
  para sugerirse a sí mismas. El motor conserva el flujo NANDA–NOC–NIC a partir
  de datos observados o derivados con trazabilidad explícita.

Las reglas de etiología, tratamiento farmacológico y clasificación de choque
no se implementan hasta tener datos y contratos suficientes.

## Decisión humana P0 de saneamiento obstétrico

- Se conserva `PAS >= 160 OR PAD >= 110` para rango severo y
  `PAS >= 140 OR PAD >= 90` para PA elevada.
- El contexto gestacional de trastorno hipertensivo exige 20 semanas o más.
- La PA elevada no crea automáticamente la etiqueta `preeclampsia`.
- Se retiró el umbral obstétrico 130/80.
- Los síntomas hipertensivos aislados activan evaluación/alarma, no un
  diagnóstico de preeclampsia.
- Salida de líquido expresa sospecha de ruptura; líquido fétido y fiebre
  expresan posible riesgo infeccioso, sin confirmar infección.
- Sangrado no fabrica dolor; náusea/vómito no fabrica deshidratación; disuria
  no fabrica infección urinaria.
- Sangrado vaginal aislado activa valoración y caracterización, no una
  clasificación de hemorragia o choque, y no fabrica compromiso fetal.
- Contracciones pretérmino exigen menos de 37 semanas tanto para booleanos
  como para texto.
- Movimientos fetales disminuidos/ausentes requieren 20 semanas o más en este
  tamizaje y activan valoración, no diagnóstico fetal.
- PA, semanas y temperatura ausentes se conservan como `None`/no valorado.
- `app.py` dejó de reinterpretar rutas mediante búsquedas en el resumen; la
  normalización obstétrica procede de `engine/obstetrico.py`.
- Farmacología permanece bloqueada.

## Bloqueos obligatorios antes de declarar v1.0 clínicamente revisada

1. Revisar todos los umbrales de `engine/interpretaciones.py`.
2. Revisar alertas de `engine/resumen.py`.
3. Revisar cada condición, nivel y acción de `engine/obstetrico.py`.
4. Revisar clínicamente la normalización centralizada en `engine/obstetrico.py`.
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
