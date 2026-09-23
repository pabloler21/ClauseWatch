# `DOCUMENT_MATCH_SYSTEM_PROMPT`

**Chequeo de correspondencia** · entre el Paso 1 y el Paso 2 del pipeline
Texto vivo en [`src/prompts/document_match_system_prompt.txt`](../../src/prompts/document_match_system_prompt.txt), cargado por [`src/document_match.py`](../../src/document_match.py)

Rol: **verificador documental**. Recibe los dos textos ya transcriptos y decide si
el segundo enmienda, reescribe o reemplaza al contrato del primero. Su salida se
valida contra `DocumentMatchVerdict` (Pydantic) vía `with_structured_output()`.
Corre con `gpt-4o-mini` (`MATCH_CHECK_MODEL_NAME` en `src/config.py`).

| Versión | Fecha | Commit | Estado |
|---|---|---|---|
| [v1](#v1) | 2026-09-23 | `34b65af` | **viva** |

---

<a name="v1"></a>
## v1 — 2026-09-23 — `34b65af`

Primera versión.

### El problema que resuelve

Sin este chequeo, si se pasan el original de un contrato y la enmienda de otro,
el Agente 2 los compara igual y devuelve "cambios" inventados dentro de un JSON
válido. Pydantic valida la forma, no que la comparación tenga sentido.

### Decisiones de diseño

| Regla | Falla que previene |
|---|---|
| *"A change of party does NOT make it a different agreement"* | rechazar una enmienda legítima que registra una cesión, fusión o cambio de razón social |
| *"Identical parties do NOT make it the same agreement"* | aceptar un NDA y una licencia firmados por las mismas dos empresas |
| *"updated version / versión actualizada … is the same agreement"* | rechazar el par 3, cuya enmienda no se titula "enmienda" |
| *"Quote the evidence verbatim"* | un veredicto sin sustento: las listas `matching_evidence` y `mismatch_evidence` obligan a citar |
| *"You do NOT compare clauses and you do NOT report changes"* | que invada el trabajo del Agente 2 |

**Una sola decisión, no dos preguntas.** La idea inicial era preguntar "¿mismas
partes?" y "¿mismo objeto?" y exigir las dos. Esa regla rechaza justo las
enmiendas que cambian una parte. La pregunta que se hace un abogado es una sola:
¿este documento modifica *este* contrato?

**Booleano, no probabilidad con umbral.** Con 11 casos no se puede calibrar un
umbral; sería un número con apariencia de medición.

### Texto completo

```text
You are a Legal Document Verification Specialist.

Your sole responsibility is to decide whether two documents belong to the same agreement: whether the second document amends, restates or replaces the specific contract contained in the first one. You do NOT compare clauses and you do NOT report changes.

How to decide:
1. Identify the agreement in the first document: its type, its parties, its execution date and its subject matter.
2. Look in the second document for how it identifies the agreement it refers to: an explicit reference to the original ("modifica el Contrato ... celebrado el ..."), the agreement type, the execution date, the parties and the subject matter.
3. Decide whether both identify the same agreement.

Rules:
- A change of party does NOT make it a different agreement. Amendments can record an assignment (cesión), a merger or a change of corporate name. If the second document explains the substitution and refers to the same original agreement, it is the same agreement.
- Identical parties do NOT make it the same agreement. The same two companies can sign several different contracts (for example, a confidentiality agreement and a software license). Compare the agreement type, execution date and subject matter, not only the names.
- A second document titled "updated version", "versión actualizada" or similar, that rewrites the full contract between the same parties with the same subject matter, is the same agreement even if it does not use the word "amendment".
- Base the verdict only on the text of the two documents. Quote the evidence verbatim, in its original language.
- Write the reason in Spanish.
```

### Resultado medido

Matriz de 11 casos de [`data/test_contracts/README.md`](../../data/test_contracts/README.md),
corrida con `uv run python src/document_match.py`:

| Casos | Resultado con `gpt-4o-mini` |
|---|---|
| 1–3, pares válidos | 3/3 aceptados (incluido el par 3, "VERSIÓN ACTUALIZADA") |
| 4–9, cruces entre pares | 6/6 rechazados |
| 10, NDA entre las mismas partes del par 1 | rechazado ✅ — *"uno es un Acuerdo de Confidencialidad y el otro es un Contrato de Licencia de Software, con fechas de celebración distintas"* |
| 11, enmienda del par 1 con cesión a Nexa | aceptado ✅ — *"modifica el mismo contrato … aunque se ha producido una cesión de derechos a Nexa Data Systems S.A."* |
| **Total** | **11/11** |

Como `gpt-4o-mini` acertó 11/11, no se corrió la comparación contra `gpt-4o`:
el modelo más barato ya cumple.

Costo y latencia, medidos en Langfuse dentro del pipeline completo (pares 2 y 3,
sin caché de prompts):

| | Tokens in → out | Costo | Latencia |
|---|---|---|---|
| Chequeo (`gpt-4o-mini`) | ~905–1.028 → ~92–104 | ~USD 0.0002 | 2–3 s |
| Corrida completa (referencia) | — | ~USD 0.027 | ~26 s |

Es menos del 1 % del costo de una corrida. Precios verificados en
[developers.openai.com](https://developers.openai.com/api/docs/models/gpt-4o-mini)
el 2026-09-23: USD 0.15/M de entrada, USD 0.60/M de salida.

### Limitaciones

- Una sola corrida de la matriz. `temperature=0` reduce la varianza pero no la
  elimina: 11/11 es un resultado, no una tasa de error.
- 11 casos, de los cuales solo 2 son difíciles. Casos que no están probados: dos
  contratos del mismo tipo entre las mismas partes con fechas distintas, o una
  enmienda que no cita al original de ninguna forma.

### Pendiente abierto

Ninguno.
