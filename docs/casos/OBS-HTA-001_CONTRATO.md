# Contrato clínico y pedagógico: OBS-HTA-001

## Estado

**BORRADOR CLÍNICO CON REVISIÓN HUMANA PARCIAL.**

La decisión humana P0 valida las reglas R01, R02, R04, R06-R10, R12-R18,
R21 y R24; valida con límites R11 y R19; y corrige R03 y R05. Farmacología,
puntuación numérica y máquina de estados permanecen bloqueadas.

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
- molestia visual importante ante la luz, considerada un síntoma visual que requiere valoración en el contexto de hipertensión grave;
- embarazo de 36 semanas.

La hipertensión grave y los síntomas neurológicos requieren evaluación urgente de un posible trastorno hipertensivo del embarazo. El escenario no establece todavía un diagnóstico médico definitivo.

`sintomas_neurologicos_relevantes` incluye cefalea y síntomas visuales de
alarma, sin afirmar que la fotofobia aislada sea diagnóstica.

`Paciente inquieta` permanece como dato complementario, con `esperado: false`;
su omisión no se penaliza.

## Responding no farmacológico

La revisión humana habilita exclusivamente estos dominios:

- reconocer urgencia;
- solicitar apoyo del equipo;
- vigilancia materna;
- vigilancia neurológica;
- valorar signos adicionales de gravedad;
- vigilancia fetal según protocolo;
- seguir protocolo institucional.

Las acciones farmacológicas permanecen bloqueadas y no se definen fármacos,
dosis, vías ni frecuencias.

## Reflecting

Reflecting queda `VALIDADO_PEDAGOGICAMENTE` con `Tanner 2006` como fundamento.
La puntuación numérica y la máquina de estados no quedan habilitadas.

## Próxima decisión

Mantener bloqueadas la farmacología, la puntuación numérica y la máquina de
estados hasta sus respectivas validaciones humanas.
