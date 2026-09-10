# `CONTEXTUALIZATION_SYSTEM_PROMPT`

**Agente 1 — ContextualizationAgent** · Paso 2 del pipeline
Definido en [`src/agents/contextualization_agent.py`](../../src/agents/contextualization_agent.py)

Rol: **Analista Legal Senior** especializado en mapeo estructural. Recibe los dos
textos parseados y produce un mapa de alineación entre secciones. Devuelve
Markdown, no JSON. **No extrae cambios**: esa es responsabilidad exclusiva del
Agente 2.

| Versión | Fecha | Commit | Estado |
|---|---|---|---|
| [v1](#v1) | 2026-09-03 | `01707f4` | **viva** — sin modificaciones |

---

<a name="v1"></a>
## v1 — 2026-09-03 — `01707f4`

Primera y única versión hasta hoy.

### Decisiones de diseño

**El rol contrasta a propósito con el del Agente 2.** "Senior Legal Contract
Analyst" contra "Senior Legal Compliance Auditor". La rúbrica 2.1 pide exactamente
esa distinción: *"system prompts altamente especializados por rol (Analista Senior
vs Auditor)"*.

**La regla negativa es el corazón del prompt:**

> *"DO NOT extract, describe, or evaluate specific clause changes (for example, do
> NOT state 'the price increased from X to Y' or 'the term was extended')."*

Es una **prohibición ejemplificada**, no abstracta. Los LLM siguen mal las
prohibiciones genéricas ("no hagas X") y bien las que traen un ejemplo del
comportamiento prohibido.

Sin esa regla, el Agente 1 haría el trabajo del Agente 2, el Agente 2 sería
redundante, y la arquitectura de dos agentes sería en realidad una de uno con un
paso duplicado. La rúbrica 1.2 pide *"separación clara"*: **esta regla es la
separación**.

La metáfora que la acompaña sirve como respuesta de una frase en la defensa:

> *"You are building a structural roadmap for an auditor, NOT performing the audit
> yourself."*

**La instrucción 2 hace funcionar el par 3.** Dice *"even if numbered differently
or rephrased"*. El documento 3 no se titula "ENMIENDA" sino "VERSIÓN ACTUALIZADA":
no es una adenda que modifica, es el contrato entero reescrito. Sin esa cláusula
del prompt, el modelo podría tratarlo como un documento sin relación con el
original.

**Salida en Markdown, no JSON.** La consigna lo permite explícitamente (*"Output
puede ser texto estructurado, no necesariamente JSON"*), y tiene sentido técnico:
el consumidor de este output es **otro LLM**, no un programa. Un LLM lee Markdown
perfectamente. Forzar JSON acá costaría tokens de schema sin ganar nada.

### Texto completo

```text
You are a Senior Legal Contract Analyst specializing in document structure mapping.

Your sole responsibility is to analyze the structure of two legal documents (an original contract and its amendment) and produce a comprehensive structural alignment map.

Instructions:
1. Identify all sections and clauses in both the original contract and the amendment.
2. Cross-reference sections between both documents:
   - Identify which clauses directly correspond to each other (even if numbered differently or rephrased).
   - Identify any new clauses introduced exclusively in the amendment.
   - Identify any clauses present in the original that are absent or omitted in the amendment.
3. For each mapped section, describe its general business and legal purpose in one concise sentence.
4. Output your analysis formatted clearly in Markdown using a comparative table followed by structural observations:
   - Section / Clause Identifier in Original Contract
   - Section / Clause Identifier in Amendment
   - Alignment Status (e.g., Corresponding, Added in Amendment, Omitted)
   - General Legal Purpose (in Spanish)

CRITICAL RULES:
- DO NOT extract, describe, or evaluate specific clause changes (for example, do NOT state "the price increased from X to Y" or "the term was extended").
- You are building a structural roadmap for an auditor, NOT performing the audit yourself.
- Write the section descriptions and structural notes in Spanish.
```

### Resultado medido

Salida real sobre el par 1, leída del input del GENERATION de `extraction_agent`
en la traza `347011016403e1a37e5ec9521b547de1` (2026-09-03):

| Identificador en Original | Identificador en Enmienda | Estado |
|---|---|---|
| 1. Otorgamiento de Licencia | 1. Otorgamiento de Licencia | Correspondiente |
| 2. Plazo | 2. Plazo | Correspondiente |
| 3. Pago | 3. Pago | Correspondiente |
| 4. Soporte | 4. Soporte | Correspondiente |
| 5. Terminación | 5. Terminación | Correspondiente |
| 6. Confidencialidad | 6. Confidencialidad | Correspondiente |
| N/A | 7. Protección de Datos | Añadido en Enmienda |

Más las observaciones estructurales (correspondencia directa, nuevas inclusiones,
ausencias, propósito consistente).

**Verificaciones:**

- ✅ **Respetó la regla negativa.** En ninguna fila menciona un valor concreto que
  haya cambiado: no dice "12 → 24 meses" ni "USD 12.000 → 15.000". Describe
  propósito, no cambios.
- ✅ Detectó la cláusula 7 como añadida solo en la enmienda.
- ✅ Mapeó las 6 correspondencias.

Costo típico: **854 prompt → 413-477 completion**, ~$0.0063.

### El handoff

El output de este agente entra literalmente en el prompt del Agente 2, bajo el
delimitador `--- STRUCTURAL ALIGNMENT MAP (AGENT 1) ---`. Verificado abriendo el
input del GENERATION de `extraction_agent` en Langfuse: la tabla de arriba aparece
completa ahí dentro.

Esa pantalla es la evidencia visual de la rúbrica 1.2, cuyo nivel insatisfactorio
es *"los agentes no colaboran (corren de forma independiente sin compartir
contexto)"*.

### Sin cambios pendientes

Este prompt no participó del fallo de eliminaciones que motivó la v2 del
`EXTRACTION_SYSTEM_PROMPT`: su trabajo es mapear estructura a nivel cláusula, y a
ese nivel el par 1 no tiene ninguna cláusula omitida — la eliminación de
`e intransferible` ocurre **dentro** de una cláusula que sí sobrevive. Detectarla
es trabajo del Agente 2 por diseño.

**Experimento pendiente que afecta a este archivo.** Correr el pipeline con
`contextual_map=""` (mapa vacío) y comparar contra la corrida normal. Es el único
test que mide si el Agente 1 aporta algo o si el Agente 2 llegaría al mismo
resultado sin él. Registrado en `CLAUDE.md`.
