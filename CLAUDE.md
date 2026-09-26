# CLAUDE.md — ClauseWatch

Proyecto integrador módulo 4, Soy Henry. Evaluado con **defensa oral**: tengo que
poder explicar y justificar cada decisión frente a un evaluador.

---

## 0. Cómo trabajás conmigo — REGLAS, no sugerencias

**1. No escribís código salvo que yo lo pida explícitamente.**
Por defecto explicás, mostrás la doc, y escribo yo. Si te pido "escribime X",
ahí sí lo escribís. Única excepción automática: boilerplate sin ninguna decisión
de diseño adentro (`.gitignore`, `.env.example`). Ante la duda, preguntás.

**2. Enseñás como profesor, no como ejecutor.**
Sos un AI Engineer senior dándome clase. Cada vez que pregunto algo, la respuesta
tiene: qué es, por qué existe, qué alternativas hay, cuál elegirías vos y por qué.
Nunca "hacé esto y listo". Si me equivoco, corregime directo y sin suavizar.

**3. Documentación verificada ANTES del código.**
Antes de cada tarea nueva que toque una librería, traés la doc oficial vigente.
Ruta: Context7 primero (`resolve-library-id` → `query-docs`); si la librería no
está ahí, web search incluyendo el año actual en la query. Citás URL y fecha.

Etiquetá cada afirmación técnica:
- ✅ **Verificado** — con URL y fecha de consulta.
- ⚠️ **De memoria** — "puede estar desactualizado, hay que confirmarlo".

Nunca presentes algo ⚠️ como si fuera ✅. Si no pudiste verificar, decilo.

**4. Este archivo no es tu cuaderno de notas.**
Acá solo va: (a) lo que dice `consigna.md`, (b) lo que yo decidí explícitamente,
(c) hechos que verificaste con fuente citada. No inventes decisiones de
arquitectura ni las escribas como cerradas si yo no las cerré.

**5. Idioma.** Conversación en español rioplatense. Código, nombres de archivo,
nombres de campo y prompts en inglés (los prompts pueden pedir salida en español).

**6. Nada de "ponytail" ni de minimalismo agresivo en este proyecto.**
No uses ese modo, ni sus comentarios `# ponytail:`, ni recortes código en nombre
de la brevedad. Este es un proyecto de aprendizaje con defensa oral: el código
tiene que poder leerlo y entenderlo alguien junior, y yo tengo que poder
explicarlo. Por lo tanto:
- Docstrings completos, con `Args`, `Returns` y `Raises`.
- Type hints en todas las firmas.
- Constantes con nombre en vez de valores sueltos en el medio del código.
- Preferí lo explícito y legible antes que lo corto e ingenioso.

**Pero los comentarios van cortos: 1 o 2 líneas.** Explican el **por qué** de una
decisión, no narran lo que la línea ya dice. Nada de bloques de comentario de
diez líneas ni ensayos dentro del código. La explicación larga va en la
conversación o en el README, no en el `.py`.

---

## 1. Qué hay que construir

Empresa ficticia **LegalMove**, tecnología legal. Compliance pierde 40+ hs
semanales comparando contratos originales contra sus enmiendas a mano.

Sistema multi-agente que recibe **dos imágenes escaneadas** (contrato original y
adenda), las lee con un modelo de visión, y con **dos agentes especializados**
extrae qué cláusulas cambiaron. Salida: **JSON validado con Pydantic**, con
**trazabilidad completa en Langfuse**.

### Stack obligatorio

| Componente | Para qué |
|---|---|
| OpenAI GPT-4o (Vision) | parsear las imágenes a texto estructurado |
| LangChain | implementar y orquestar los dos agentes |
| Pydantic | validar y estructurar el output final |
| Langfuse | trazado completo del workflow |
| Python + python-dotenv | base y variables de entorno |

### Los 5 pasos

1. **Parsing multimodal** — `parse_contract_image(path)`: encode base64 + llamada
   multimodal a GPT-4o. Se ejecuta 2 veces (original y enmienda). Observabilidad
   por spans de Langfuse.
2. **Agente 1 `ContextualizationAgent`** — recibe los dos textos parseados.
   Produce un análisis de estructura comparada: qué secciones existen en ambos,
   cómo se corresponden, propósito de cada bloque. Output puede ser texto
   estructurado, **no necesariamente JSON**. **No extrae cambios.**
3. **Agente 2 `ExtractionAgent`** — recibe el mapa del Agente 1 **más ambos
   textos**. Identifica, aísla y describe cada cambio. Distingue **adiciones,
   eliminaciones y modificaciones**. Output: JSON estructurado.
4. **Validación Pydantic** — `ContractChangeOutput`. Vía `model_validate()` o
   structured outputs con `response_format`.
5. **Trazabilidad Langfuse** — span raíz `contract-analysis` con hijos
   `parse_original_contract`, `parse_amendment_contract`,
   `contextualization_agent`, `extraction_agent`. Cada span con input, output,
   latencia y metadata.

---

## 2. Entregables (repo público de GitHub)

| Archivo | Contenido |
|---|---|
| `src/main.py` | entry point, acepta dos paths de imágenes como argumentos |
| `src/agents/contextualization_agent.py` | Agente 1, system prompt y lógica propios |
| `src/agents/extraction_agent.py` | Agente 2, system prompt y lógica propios |
| `src/image_parser.py` | validación, encoding base64, llamadas multimodales |
| `src/models.py` | `ContractChangeOutput` con los tres campos |
| `data/test_contracts/` | mínimo 2 pares (4 imágenes) + README explicativo |
| `README.md` | diagramas, arquitectura, setup, uso, decisiones técnicas |
| `requirements.txt` + `.env.example` | versiones fijadas + template de env vars |

---

## 3. Rúbrica — 100 pts, apuntar a "Excelente"

| Criterio | Pts | Nivel excelente |
|---|---|---|
| 1.1 Parsing multimodal | 15 | GPT-4o Vision + base64. Texto preciso **respetando jerarquías** (cláusulas/secciones) |
| 1.2 Arquitectura 2 agentes | 15 | Separación clara + handoff donde el 2do **usa el mapa del 1ro** |
| 1.3 Validación Pydantic | 10 | Cumple estricto el modelo. Maneja `ValidationError` con mensajes claros |
| 2.1 Calidad del prompting | 15 | System prompts **altamente especializados** por rol (Analista Senior vs Auditor) |
| 2.2 Gestión API y errores | 10 | Timeouts, límites de tokens, encoding. Env vars bien usadas |
| 3.1 Trazabilidad | 15 | Traza padre + jerarquía de spans. Inputs, outputs, latencia, tokens |
| 4.1 Estructura y README | 10 | Código modular. README con diagrama de arquitectura y justificación técnica |
| 5.1 Defensa en vivo | 10 | Explica decisiones con fluidez, muestra Langfuse, demo con 2 casos |

**Frases exactas que bajan la nota** (citadas de la rúbrica, sirven de checklist):
- 1.3 satisfactorio: *"faltan descripciones de campo/tipado"*
- 2.2 satisfactorio: *"algunas claves o configuraciones están hardcodeadas"*
- 3.1 satisfactorio: *"de forma plana (sin jerarquía de spans)"*, *"faltan métricas críticas de tokens/costo"*
- 1.2 insatisfactorio: *"los agentes no colaboran (corren de forma independiente sin compartir contexto)"*

---

## 4. Estado real del repo — verificado 2026-09-23

```
CLAUDE.md          consigna.md        pyproject.toml     uv.lock
requirements.txt   .env (ignorado)    .env.example       .gitignore
.gitattributes     .python-version    README.md (~20 KB, completo)
src/config.py      src/models.py      src/image_parser.py    src/main.py
src/document_match.py  src/parse_cache.py
tests/test_parse_cache.py
src/prompts/           __init__.py (load_prompt) + los 4 system prompts en .txt
src/agents/contextualization_agent.py
src/agents/extraction_agent.py
data/test_contracts/   8 imágenes = 3 pares + 2 de correspondencia + README.md
docs/prompts/          historial versionado de los 4 system prompts + README
docs/superpowers/      spec y plan del registro de transcripciones
data/parsed_contracts/ registro local de transcripciones (gitignoreado)
```

**Hecho — pipeline completo de los 5 pasos más el chequeo de correspondencia,
corriendo end-to-end:**
- `src/prompts/` — cada system prompt es un `.txt` con exactamente lo que recibe
  el modelo. `load_prompt(name)` lo lee con utf-8 al importar el módulo y falla si
  el archivo falta o está vacío. Las constantes (`EXTRACTION_SYSTEM_PROMPT`,
  etc.) conservan su nombre. Verificado byte a byte contra los strings anteriores.
- `src/config.py` — `MODEL_NAME`, `MODEL_TEMPERATURE`, `MODEL_TIMEOUT_SECONDS`
  (60), `MODEL_MAX_TOKENS` (4000), más `MATCH_CHECK_MODEL_NAME`
  (`openai:gpt-4o-mini`) y `MATCH_CHECK_MAX_TOKENS` (1000). Sin credenciales.
- `src/models.py` — `ClauseChange` (`section`, `change_type:
  Literal["addition","deletion","modification"]`, `detail`) y
  `ContractChangeOutput` con los 3 campos de la consigna **más** `changes:
  list[ClauseChange]`. Todos con `Field(description=...)`. `@model_validator`
  `sections_must_match_changes` exige que las secciones de `changes` coincidan
  con `sections_changed`. `DocumentMatchVerdict` (`same_agreement`,
  `matching_evidence`, `mismatch_evidence`, `reason`) para el chequeo.
- `src/image_parser.py` — Paso 1. `validate_image_file()` +
  `encode_image_to_base64()` + `parse_contract_image()`. Bloques multimodales
  estándar, guardia contra truncamiento por `finish_reason == "length"`.
- `src/agents/contextualization_agent.py` — Paso 2. `analyze_contract_structure()`,
  rol "Senior Legal Contract Analyst". Devuelve Markdown. Regla negativa que le
  prohíbe extraer cambios. Prompt v1.
- `src/agents/extraction_agent.py` — Paso 3 + 4. `extract_contract_changes()`,
  rol "Senior Legal Compliance Auditor". `with_structured_output(ContractChangeOutput)`,
  `ValidationError` y `openai.LengthFinishReasonError` → `RuntimeError`.
  Prompt **v4**.
- `src/document_match.py` — chequeo de correspondencia entre el parsing y los
  agentes. `check_document_match()` devuelve un `DocumentMatchVerdict`; no
  decide qué hacer con él. `gpt-4o-mini`, 11/11 en la matriz de prueba, ~USD
  0.0002 y 2-3 s por corrida (medido en Langfuse). Prompt v1.
- `src/parse_cache.py` — registro de transcripciones (2026-09-26). JSON por
  entrada en `data/parsed_contracts/`, clave `sha256(sha256(imagen) | modelo |
  sha256(prompt))`, escritura `.tmp` + `replace()`, `CacheEntryCorruptError`.
  `main.py` lo consulta en `_parse_with_cache()`, marca `parse_cache`
  (hit/miss/refresh) en la metadata del span y acepta `--refresh-cache`.
  Medido en el par 1: 23 s → 14 s, USD 0.0300 → 0.0189; la traza del acierto no
  tiene generaciones bajo los spans de parsing (✅ API de Langfuse, 2026-09-26).
  5 tests `unittest` en `tests/`.
- `src/main.py` — Paso 5. CLI `argparse` con `--skip-match-check`, span raíz
  `contract-analysis` con cinco hijos `@observe`, un `CallbackHandler` por
  etapa. Si el veredicto es negativo lanza `DocumentMismatchError` antes de los
  agentes (exit 3); si el chequeo falla, sigue y marca el span `WARNING`.
  `main()` genera el trace id y resuelve la URL fuera del span. JSON a stdout,
  progreso/errores/link a stderr, stdout forzado a UTF-8. Exit codes como
  constantes: 0, 1, 3 (2 es de argparse).
- `README.md` — completo: arquitectura con Mermaid, grafo de dependencias,
  setup, uso, salida de ejemplo, observabilidad, decisiones técnicas, validación
  contra ground truth (v1→v3 del prompt), limitaciones.
- `docs/prompts/` — historial versionado. Viva: transcripción v1,
  contextualización v1, extracción v4 (3/3 pares exactos contra ground truth),
  correspondencia v1 (11/11).
- Entorno: `uv` + `pyproject.toml` (5 dependencias directas, sin muertas).
  Instalado: `langchain 1.3.18`, `langchain-core 1.6.1`, `langchain-openai 1.6.0`,
  `openai 3.7.0`, `pydantic 2.13.5`, `python-dotenv 1.2.3`, `langfuse 4.15.1`.
  `.env` y `.env.example` usan `LANGFUSE_BASE_URL`.

**Inconsistencias de la revisión del 2026-09-23 — todas corregidas**
(`9c21e9b`, commits `fix:` y `docs:` de esa fecha). Una estaba mal diagnosticada:
el truncamiento del Agente 2 no llegaba como error de Pydantic sino como
`openai.LengthFinishReasonError` (✅ reproducido con `max_tokens=30`), que
`main.py` mostraba como `[ERROR INESPERADO]`.

### Traza de referencia verificada en Langfuse — 2026-09-03 (prompts v1)

Jerarquía real observada en Langfuse Cloud US (par 1), corrida de 27,14 s:

```
contract-analysis            27.14s   $0.026147   Σ 6.343 tokens
├── parse_original_contract   9.19s   $0.005745
│   └── ChatOpenAI            6.81s   1.286 → 253    (GENERATION)
├── parse_amendment_contract  7.06s   $0.006145
│   └── ChatOpenAI            7.05s   1.286 → 293    (GENERATION)
├── contextualization_agent   5.61s   $0.006905
│   └── ChatOpenAI            5.61s     854 → 477    (GENERATION)
└── extraction_agent          4.63s   $0.007353
    └── RunnableSequence      4.63s                  (CHAIN)
        ├── ChatOpenAI        4.62s   1.545 → 349    (GENERATION)
        └── RunnableLambda                           (parser Pydantic)
```

Con el prompt v4 y el campo `changes`, el costo total medido sobre el par 1 es
**$0.027727** por corrida, y el agente de extracción sube a 2.285 → 590 tokens,
$0.011612 (brazo C, `docs/prompts/extraction_system_prompt.md`). Con esos
números, el parsing es ~43 % del costo y los dos agentes ~57 %.

Cubre la rúbrica 3.1 nivel excelente: traza padre, jerarquía real (no plana),
inputs/outputs por span, latencia, tokens y costo por generación.

`extraction_agent` cuelga de un `RunnableSequence` en vez de un `ChatOpenAI`
directo porque `with_structured_output()` devuelve una cadena compuesta
(modelo + parser); el `RunnableLambda` es ese parser. Es una diferencia
esperada, no un error.

### Ground truth

Vive en **`data/test_contracts/README.md`**, con los tres pares analizados
cláusula por cláusula. Fuente única: no duplicar esas tablas acá.

Resumen: par 1 = 5 modificaciones + 1 adición + 1 sin cambios. Par 2 = 4
modificaciones + 1 adición + 2 sin cambios. Par 3 = 3 modificaciones + 2 sin
cambios.

Partes de cada par: par 1 TechNova / DataBridge, par 2 Orion / GreenWave,
par 3 CloudMetrics / RetailPulse. La matriz de 11 casos del chequeo de
correspondencia también vive en `data/test_contracts/README.md`; los dos casos
difíciles son `documento_4_original.jpg` (NDA entre las partes del par 1) y
`documento_1_enmienda_cesion.jpg` (cesión a Nexa Data Systems). Ambas imágenes
se generaron con Pillow desde un script fuera del repo.

**Limitación conocida del set: ningún par elimina una cláusula entera.** La
única eliminación es interna (par 1, cláusula 1: desaparece "e intransferible").
Documentada como limitación en el README. Sigue sin decidirse si se agrega un
par 4.

---

## 5. Decisiones que ya tomé yo

**`uv` + `uv.lock` como fuente de verdad, `requirements.txt` derivado.** El
profesor confirmó que `uv` + `pyproject.toml` + `uv.lock` cumple el requisito de
versiones fijadas. Igual se agregó un `requirements.txt` generado con
`uv export` (`2d7dad4`); el README explica que es derivado, no la fuente.

**`main.py` de la raíz borrado** — era el placeholder de `uv init`. El entry
point va en `src/main.py`.

**Prompts en archivos, no en el código (2026-09-23, `de14498`).** Cada system
prompt vive en `src/prompts/<nombre>.txt` y el módulo lo carga con
`load_prompt()`. `.txt` y no `.md` para no confundir el texto vivo con su
historial en `docs/prompts/*.md`.

**Chequeo de correspondencia entre documentos (2026-09-23).** Corre después del
parsing, sobre el texto de GPT-4o, y antes de los agentes. Descartado: OCR local
con Tesseract + Jev antes del parsing (reintroducía una dependencia de OCR,
sumaba un proveedor fuera del stack, decidía con el texto peor, y "¿mismas
partes?" rechazaría una cesión). Una sola decisión `same_agreement` en vez de
dos preguntas combinadas con AND; booleano en vez de umbral (11 casos no
calibran nada). Fail-open ante fallo del chequeo; `--skip-match-check` ante un
falso rechazo. Precios verificados 2026-09-23 en
https://developers.openai.com/api/docs/models/gpt-4o-mini (USD 0.15/M in,
0.60/M out) y https://developers.openai.com/api/docs/models/gpt-4o (USD 2.50/M
in, 10/M out).

**`Field(description=...)` incorporadas (`f0c77f4`).** Se midió con y sin sobre
el par 1: salida idéntica, +109 tokens de prompt. Se incorporaron igual porque la
rúbrica 1.3 las pide. El README dice que no mejoran la salida.

**Campo `changes` + `Literal` + `model_validator` (`8d2183f`).** Cuarto campo por
encima de los tres de la consigna, para que el tipo de cambio sea consultable por
código. Costo conocido: +80 % de tokens de completion en el agente por la
redundancia con `summary_of_the_change` (documentado como limitación).

**Configuración del modelo centralizada en `src/config.py` (`1e2c076`).**
Constantes con nombre, no variables de entorno. Riesgo residual con la rúbrica
2.2: no es configurable desde afuera sin editar el archivo; el README lo declara
como limitación.

**Registro de transcripciones: opción B (2026-09-26).** Caché por hash exacto
ahora; base vectorial como fase 2 para "¿a qué contrato corresponde esta
enmienda suelta?", sin implementar. Descartada la vectorial para el caché: habría
que parsear antes de buscar, y la similitud confunde una enmienda con su
original. Spec en `docs/superpowers/specs/2026-09-26-parse-cache-design.md`.

**Llamadas directas en vez de `create_agent`.** Ninguno de los dos agentes tiene
tools; justificado en el README (el Agente 1 es un `invoke()` directo, el Agente
2 la cadena de `with_structured_output()`).

**Dependencias muertas eliminadas (`28b49d1`)** — `pillow`, `pytesseract` y
`dotenv`. **`LANGFUSE_HOST` renombrado a `LANGFUSE_BASE_URL` (`83d204d`).**

**Nombres de spans** — dos wrappers en `main.py` con `@observe(name=...)`. El
nombre del span es responsabilidad del orquestador, no del parser.

**Span raíz devuelve solo `ContractChangeOutput` (`20fed01`, 2026-09-22).**
`@observe` registra el valor de retorno como output del span
(✅ `observe.py:552-553` del SDK 4.15.1: `span.update(output=result)`); devolver
la tupla `(resultado, url)` ensuciaba el span, y `get_trace_url()` hace un GET a
la API (✅ `client.py:2428-2437`) que se contaba en la latencia. `main()` genera
el id con `create_trace_id()` y lo pasa con el kwarg `langfuse_trace_id`
(✅ `observe.py:181`, consumido vía `kwargs.pop()`), y resuelve la URL fuera del
span. Sin id explícito, `get_trace_url()` después de cerrar el span devuelve
`None` con `"Context error: No active span in current context"`
(✅ reproducido, `client.py:1395-1404`).

**El link de la traza se imprime también cuando el pipeline falla (`4e8ba33`)**
y **un fallo de telemetría no tumba el reporte (`8564899`).**

---

## 6. Abierto — resolver con evidencia, no discutiendo

**Chequeo de correspondencia: robustez.** 11/11 en una sola corrida. Si
importa poder afirmar una tasa de error, repetir la matriz y sumar casos
difíciles (mismo tipo de contrato entre las mismas partes con fechas distintas;
enmienda que no cita al original).

**Configurabilidad del modelo por entorno.** Ver §5: hoy se edita
`src/config.py`. Decidir si se leen overrides desde `.env` para cerrar el
riesgo de la rúbrica 2.2 o si se defiende la decisión tal cual.

**Par 4 con eliminación de cláusula entera.** Ver §4, ground truth.

**Fase 2 del registro: base vectorial.** Ver §5. Sin spec todavía.

**OPCIONAL — Ablation del ContextualizationAgent (flag `--no-context-map`).**
Diferido por decisión mía el 2026-09-10: es un adorno frente a lo que falta.

Qué sería: un flag de `argparse` que saltea al Agente 1 por completo y arma el
prompt del Agente 2 sin la sección del mapa (omitida entera, no vacía — un
encabezado anunciando un mapa ausente mide "mapa roto", no "sin mapa").
Correr los pares 1 y 3, dos repeticiones por brazo, y comparar salida, tokens,
latencia y costo.

Para qué serviría: hoy la evidencia del handoff es que el mapa **aparece** en el
prompt del Agente 2 (verificado en Langfuse). Eso prueba transmisión, no
utilidad. El ablation respondería "¿y si sacás el Agente 1, cambia algo?".

El par 3 es el mejor caso de prueba, no el par 1: su enmienda se titula "VERSIÓN
ACTUALIZADA" y el Agente 1 tiene que reconocer la correspondencia igual. En el
par 1 la correspondencia es 1↔1 y cualquier modelo la resuelve solo.

El Agente 1 se queda pase lo que pase: lo exige la consigna. El experimento no
decide si se borra, decide qué se puede afirmar sobre él en la defensa.

---

## 7. Disciplina de versiones

El ecosistema se movió mucho; muchos tutoriales que voy a googlear están rotos.
No copiar patrones sin verificarlos contra la doc oficial vigente.

**Trampa confirmada — mensajes multimodales en LangChain**
✅ Verificado en https://docs.langchain.com/oss/python/langchain/messages (2026-09-02)

El formato estándar actual de bloque de imagen es:

```python
{"type": "image", "base64": b64, "mime_type": "image/jpeg"}
```

y va en `content_blocks=[...]`. El formato `{"type": "image_url", "image_url":
{"url": "data:image/jpeg;base64,..."}}` es el **provider-native** de OpenAI:
funciona, pero ata el código al proveedor. Filtro rápido: si el ejemplo dice
`image_url`, es el camino viejo.

**Langfuse — verificado 2026-09-03 contra el SDK 4.15.1 instalado y la doc**
✅ https://langfuse.com/integrations/frameworks/langchain (2026-09-03)
✅ Introspección del paquete instalado (`langfuse/_client/client.py`)

- Imports vigentes: `from langfuse import get_client, observe` y
  `from langfuse.langchain import CallbackHandler`. El `Langfuse(...)` +
  `langfuse.trace(...)` de los tutoriales viejos (SDK v2) ya no existe.
- `client.get_trace_url(trace_id=None)` existe y devuelve la URL de la traza
  activa. Reemplaza a `api.trace.list(...)`, que era el workaround del v2.
- **`LANGFUSE_HOST` está deprecado.** El SDK lo sigue leyendo, pero como
  fallback. Orden real de resolución en `client.py:341-343`:
  `base_url=` (argumento) → `LANGFUSE_BASE_URL` → `LANGFUSE_HOST` →
  `https://cloud.langfuse.com` (¡región EU!). Ya renombrada a
  `LANGFUSE_BASE_URL` en `.env` y `.env.example` (`83d204d`): si el fallback
  desaparece en una versión futura, las trazas no se van silenciosamente a EU.
- El `CallbackHandler` no se configura con credenciales: llama a `get_client()`
  internamente y se engancha al span de OpenTelemetry que esté activo en ese
  momento. Por eso los spans de LangChain aparecen anidados bajo el `@observe`
  correspondiente sin que haya que pasarles ningún parent id.
- Un único `CallbackHandler()` alcanza para todo el pipeline: mantiene su estado
  por corrida en un dict indexado por UUID de run. Crear uno por etapa (como
  hace hoy `main.py`) funciona igual, pero no es necesario.
- `update_current_span(level=..., status_message=..., metadata=...)` existe en
  4.15.1 (✅ `client.py:1492`); `SpanLevel = Literal["DEBUG", "DEFAULT",
  "WARNING", "ERROR"]` (✅ `langfuse/types.py:43`).
- Los `usage_details` de una generación separan `input` de `input_cache_read`:
  OpenAI cachea prompts repetidos, y una corrida justo después de otra con las
  mismas imágenes reporta `input` mucho menor. Para medir costo, usar corridas
  sin caché o sumar ambos campos.
