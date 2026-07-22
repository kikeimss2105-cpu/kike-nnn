# Estado real de KIKE-NNN v19

**Fecha de inventario:** 2026-07-22  
**Rama:** `feature/tanner-caso-001`  
**Base protegida:** `v19-pre-tanner-2026-07-22`  
**Commit de infraestructura:** `e1aa34b`

## 1. Línea base técnica

| Control | Resultado |
|---|---|
| Python | 3.14.4 |
| Compilación | Correcta |
| Golden Tests | 98 aprobados, 0 fallos |
| Pytest | 1 prueba aprobada |
| Respaldo externo | Creado |

## 2. Estructura actual

| Componente | Estado | Evidencia | Observación |
|---|---|---|---|
| Carga de catálogos | PROBADO | `engine/carga.py` | Carga datos mediante pandas |
| Normalización de texto | PROBADO | `engine/texto.py` | Incluye consolidación de hallazgos |
| Motor NANDA | PROBADO | `engine/motor.py` | Búsqueda basada en texto y enlaces |
| Interpretación de escalas | PROBADO | `engine/interpretaciones.py` | Braden, EVA, Glasgow, caídas, SpO2, FR y PA obstétrica |
| Motor obstétrico | PROBADO | `engine/obstetrico.py` | Módulo clínico más extenso |
| Patrones de Gordon | PARCIAL | `engine/gordon.py` | Implementación incompleta |
| Plan NOC-NIC | PROBADO | `engine/plan.py` | Metas, indicadores, actividades y fundamentos |
| Reporte docente | IMPLEMENTADO | `engine/docente.py` | Validación pedagógica externa pendiente |
| Resumen y alertas | PROBADO | `engine/resumen.py` | Generación de resumen y alertas |
| Exportadores | IMPLEMENTADO | `utils/exportadores.py` | Sin pruebas unitarias independientes visibles |
| Motor contextual | AUSENTE | Sin módulo | Solo existe como propuesta |
| Modelo Tanner | AUSENTE | Sin módulo | No implementado |
| Máquina de estados | AUSENTE | Sin módulo | No implementada |
| Tutor socrático | AUSENTE | Sin módulo | No implementado |
| Debriefing Tanner | AUSENTE | Sin módulo | No implementado |
| Validación clínica formal | NO DEMOSTRADA | Sin evidencia en repositorio | Requiere revisión humana y bibliográfica |

## 3. Riesgos arquitectónicos

1. `app.py` contiene 1091 líneas y coordina demasiadas responsabilidades.
2. `engine/obstetrico.py` contiene 336 líneas y representa una zona de alto impacto clínico.
3. Los Golden Tests están concentrados en un corredor secuencial.
4. Las pruebas actuales protegen regresiones, pero no equivalen a validación clínica.
5. El sistema depende parcialmente de coincidencias textuales.
6. No existe todavía un motor contextual completo.
7. No existe separación entre simulación y motor NNN.
8. Tanner no debe integrarse directamente en `app.py`.
9. La puntuación pedagógica todavía no está definida ni validada.

## 4. Decisión de integración

Tanner se desarrollará inicialmente como módulo aislado y demostrador independiente.

Estructura prevista:

    engine/tanner/
    ├── __init__.py
    ├── modelos.py
    ├── noticing.py
    ├── interpreting.py
    ├── responding.py
    ├── reflecting.py
    └── debriefing.py

La interfaz inicial será:

    app_tanner_demo.py

No se modificará `app.py` durante el primer prototipo.

## 5. Caso inicial

Identificador provisional:

    OBS-HTA-001

Tema:

Paciente de 36 semanas de gestación con hipertensión grave y manifestaciones neurológicas de alarma.

Estado:

    PROPUESTO

Antes de programarlo deben definirse:

- indicios críticos;
- distractores plausibles;
- conceptos de interpretación;
- acciones esperadas;
- acciones inseguras;
- evolución por estados;
- debriefing;
- fuentes clínicas;
- revisión humana.

## 6. Definición de terminado

Un componente solo podrá marcarse como terminado cuando:

1. exista;
2. compile;
3. tenga pruebas;
4. las pruebas pasen;
5. esté documentado;
6. pueda explicarse;
7. no dependa de afirmaciones clínicas sin fuente.

## 7. Alcance congelado

Durante la Operación TANNER-UNO no se añadirán:

- nuevas escalas;
- nuevos dominios clínicos;
- voz;
- avatar;
- aplicación móvil;
- integración hospitalaria;
- motor fisiológico universal;
- nuevos modelos de IA;
- funciones cosméticas;
- estudios multicéntricos.

Todo lo nuevo se registrará para trabajo futuro.
