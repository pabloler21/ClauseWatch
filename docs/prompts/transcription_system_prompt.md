# `TRANSCRIPTION_SYSTEM_PROMPT`

**Paso 1 — Parsing multimodal**
Definido en [`src/image_parser.py`](../../src/image_parser.py)

Rol: **motor de transcripción**. Recibe la imagen de un contrato codificada en
base64 y devuelve su texto. Se ejecuta dos veces por análisis, una por documento.

| Versión | Fecha | Commit | Estado |
|---|---|---|---|
| [v1](#v1) | 2026-09-03 | `c2293d4` | **viva** — sin modificaciones |

---

<a name="v1"></a>
## v1 — 2026-09-03 — `c2293d4`

Primera y única versión hasta hoy.

### La premisa del diseño

GPT-4o **no es un OCR**: razona sobre la imagen, y por eso respeta la jerarquía del
documento — cosa que un OCR tradicional no hace. Pero como razona, también puede
resumir, corregir o reformular por iniciativa propia.

Cada regla del prompt neutraliza uno de esos modos de falla:

| Regla | Falla que previene |
|---|---|
| *"Reproduce the text verbatim. Do not summarize, rephrase, translate or explain."* | el modelo resume un contrato largo |
| *"Keep the original clause numbering and headings on their own line"* | pierde la jerarquía — la **rúbrica 1.1 pide literalmente** *"respetando jerarquías (cláusulas/secciones)"* |
| *"Do not convert 'USD 12.000' into '$12,000'"* | normalización de números. Rompería el par 3, donde los cambios son `1.200 → 1.250` y `99,5% → 99,9%`: un dígito |
| *"Do not fix typos, spelling or grammar."* | el modelo "mejora" el documento y deja de ser el original |
| *"Preserve the blank line that separates one clause from the next."* | el Agente 1 no puede segmentar cláusulas |
| *"Output only the transcription. No preamble…"* | *"Aquí está la transcripción del contrato:"* se cuela en el texto |

**"engine", no "assistant".** La primera línea asigna un rol mecánico, no
conversacional. Es deliberado.

### Texto completo

```text
You are a document transcription engine.
Transcribe the contract shown in the image exactly as it is written.

Rules:
- Reproduce the text verbatim. Do not summarize, rephrase, translate or explain.
- Keep the original clause numbering and headings on their own line, exactly as
  they appear in the document (for example: "3. Pago").
- Keep every number, amount, percentage and date in its original notation.
  Do not convert "USD 12.000" into "$12,000".
- Do not fix typos, spelling or grammar. An error in the source document is part
  of the source document.
- Preserve the blank line that separates one clause from the next.
- Output only the transcription. No preamble, no commentary, no closing remarks.
```

### Resultado medido

Verificado sobre `documento_1_original.jpg` (2026-09-10), comparando la salida
contra la imagen fuente:

| Criterio | Resultado |
|---|---|
| Numeración de cláusulas (`1.`, `2.`, `3.`…) | ✅ preservada |
| Montos sin normalizar (`USD 12.000`) | ✅ preservado, no lo convirtió a `$12,000` |
| Calificativos legales (`e intransferible`, `únicamente`) | ✅ preservados |
| Líneas en blanco entre cláusulas | ✅ preservadas |
| Título y preámbulo | ✅ completos |
| Preámbulo sin agregados | ✅ sin comentarios del modelo |

Costo típico por imagen: **1.286 prompt → 253 completion**, ~$0.0057.

**Este prompt quedó descartado como causa** del fallo de eliminaciones que motivó
la v2 del `EXTRACTION_SYSTEM_PROMPT`: la información que el Agente 2 no reportaba
(`e intransferible`) **sí estaba** en la transcripción.

### Nota

Las negritas del documento original (`TechNova S.A.`, `DataBridge Soluciones
S.R.L.`) no se preservan como formato. El prompt no pide Markdown, así que es
esperable y no afecta al pipeline: ningún paso posterior depende del formato de
énfasis.

### Sin cambios pendientes

No se identificó ningún fallo que justifique una v2. Si aparece uno, se agrega
acá abajo siguiendo la convención del [README](README.md).
