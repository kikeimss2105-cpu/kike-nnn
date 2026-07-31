# Contrato clínico y pedagógico: OBS-HTA-001

## Estado

**BORRADOR CLÍNICO. NO IMPLEMENTADO.**

## Propósito

Construir el primer caso demostrable de KIKE-NNN basado en las cuatro fases del Modelo de Juicio Clínico de Tanner:

1. Noticing.
2. Interpreting.
3. Responding.
4. Reflecting.

## Alcance actual

El contrato define:

- escena inicial;
- indicios críticos;
- distractores;
- conceptos mínimos de interpretación;
- dominios preliminares de respuesta;
- elementos de reflexión;
- información que debe registrar el sistema.

Todavía no define:

- medicamentos;
- dosis;
- vías;
- órdenes clínicas;
- puntuaciones numéricas;
- transiciones fisiológicas;
- diagnóstico médico automático.

## Decisiones de seguridad

1. El caso es exclusivamente educativo.
2. Las claves clínicas serán deterministas y revisables.
3. La IA no podrá cambiar la clave clínica.
4. No se evaluará mediante frases literales.
5. No se otorgará una puntuación arbitraria antes de validar la rúbrica.
6. Las intervenciones farmacológicas permanecerán bloqueadas hasta contar con fuente y revisión clínica.
7. El primer motor de evolución utilizará estados discretos específicos del caso.

## Evidencia inicial

El escenario utiliza como indicios críticos:

- presión arterial de 165/115 mmHg;
- cefalea intensa;
- molestia importante ante la luz, considerada un síntoma neurológico que requiere valoración;
- embarazo de 36 semanas.

La hipertensión grave y los síntomas neurológicos requieren evaluación urgente de un posible trastorno hipertensivo del embarazo. El escenario no establece todavía un diagnóstico médico definitivo.

## Próxima decisión

Validar la fase Noticing antes de escribir código.
