# Historial de prompts — ClauseWatch

Un archivo por cada system prompt del pipeline. Cada archivo guarda **todas** las
versiones que ese prompt tuvo, en orden cronológico, con el texto completo de cada
una y el motivo del cambio.

## Para qué existe esta carpeta

Los prompts son el componente del sistema que más se toca y del que menos queda
registro. Un `git diff` sobre un prompt muestra *qué* letras cambiaron, pero no
**por qué** cambiaron ni **qué se midió** para saber que el cambio sirvió.

Esta carpeta guarda esa segunda parte. Sirve para tres cosas:

1. **Defensa oral (rúbrica 2.1 y 5.1).** Poder responder "¿por qué el prompt dice
   eso?" con la corrida que lo motivó, y no con "me pareció que quedaba mejor".
2. **No repetir experimentos.** Si una regla ya se probó y no sirvió, queda escrito.
3. **Atribuir mejoras.** Cuando el resultado cambia, saber cuál edición lo produjo.

## Archivos

| Archivo | Constante | Ubicación en el código | Paso | Versión viva |
|---|---|---|---|---|
| [`transcription_system_prompt.md`](transcription_system_prompt.md) | `TRANSCRIPTION_SYSTEM_PROMPT` | `src/image_parser.py` | 1 — Parsing multimodal | v1 |
| [`contextualization_system_prompt.md`](contextualization_system_prompt.md) | `CONTEXTUALIZATION_SYSTEM_PROMPT` | `src/agents/contextualization_agent.py` | 2 — Agente 1 | v1 |
| [`extraction_system_prompt.md`](extraction_system_prompt.md) | `EXTRACTION_SYSTEM_PROMPT` | `src/agents/extraction_agent.py` | 3 — Agente 2 | **v2** |

## Convención para agregar una versión

Las versiones se **agregan al final**, nunca se reescribe una anterior. Un prompt
viejo que quedó registrado como "no funcionó" vale tanto como el que funcionó.

Cada versión nueva lleva:

- **Encabezado** `## vN — <fecha> — <commit o "sin commitear">`
- **Qué cambió** respecto de la versión anterior, como tabla o lista corta.
- **Por qué**: el fallo observado que motivó el cambio, con evidencia (traza de
  Langfuse, salida concreta, comparación contra el ground truth).
- **Texto completo** de la versión, en un bloque de código. Completo, no un diff:
  el archivo tiene que poder leerse sin reconstruir nada.
- **Resultado medido**: qué se corrió, qué pasó, cuánto costó en tokens.

La fuente de verdad del texto **vivo** es siempre el `.py`. Este archivo es el
registro histórico y el razonamiento; si los dos se contradicen, gana el `.py` y
hay que corregir el `.md`.

## Ground truth

Todas las mediciones se comparan contra
[`data/test_contracts/README.md`](../../data/test_contracts/README.md), que analiza
los tres pares de contratos cláusula por cláusula. Ese archivo se escribió leyendo
las imágenes a mano, **antes** de correr ningún modelo.
