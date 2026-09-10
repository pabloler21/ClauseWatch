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

## 4. Estado real del repo — verificado 2026-09-03

```
CLAUDE.md          consigna.md        pyproject.toml     uv.lock
.env (ignorado)    .env.example       .gitignore         README.md (VACÍO, 0 bytes)
src/models.py      src/image_parser.py    src/main.py
src/agents/contextualization_agent.py
src/agents/extraction_agent.py
data/test_contracts/   6 imágenes = 3 pares + README.md (ground truth)
```

**Hecho — pipeline completo de los 5 pasos, corriendo end-to-end:**
- `src/models.py` — `ContractChangeOutput` con los 3 campos y docstring de clase.
  Sin `Field(description=...)`. Ver §6.
- `src/image_parser.py` — Paso 1. `validate_image_file()` +
  `encode_image_to_base64()` + `parse_contract_image()`. Bloques multimodales
  estándar (`{"type": "image", "base64": ..., "mime_type": ...}`), timeout 60 s,
  `max_tokens=4000`, guardia contra truncamiento por `finish_reason == "length"`.
- `src/agents/contextualization_agent.py` — Paso 2. Agente 1, rol "Senior Legal
  Contract Analyst". Devuelve Markdown, no JSON. Regla negativa explícita que le
  prohíbe extraer cambios.
- `src/agents/extraction_agent.py` — Paso 3 + 4. Agente 2, rol "Senior Legal
  Compliance Auditor". Usa `with_structured_output(ContractChangeOutput)`.
- `src/main.py` — Paso 5. CLI con `argparse`, span raíz `contract-analysis` y
  cuatro hijos vía `@observe`, `CallbackHandler` de LangChain por etapa,
  `flush()` en `finally`, imprime JSON + URL de la traza.
- 3 pares de contratos de prueba en `data/test_contracts/` (la consigna pide
  mínimo 2), nombrados `documento_N_original.jpg` / `documento_N_enmienda.jpg`
  — el número del par va primero para que al ordenar queden los pares juntos.
  Su `README.md` es el ground truth.
- Entorno: `uv` + `pyproject.toml`. Instalado: `langchain 1.3.18`,
  `langchain-core 1.6.1`, `langchain-openai 1.6.0`, `openai 3.7.0`,
  `pydantic 2.13.5`, `python-dotenv 1.2.3`, `langfuse 4.15.1`.
- `.env` creado y gitignoreado. `.env.example` como template.

**Falta:**
- `README.md` de la raíz: está **vacío (0 bytes)**. Es el entregable de la
  rúbrica 4.1 (10 pts) y hoy vale 0.
- Limpiar dependencias muertas de `pyproject.toml`: `pillow` y `pytesseract`
  quedaron de una idea de OCR local que se descartó, y `dotenv` (0.9.9) es un
  paquete distinto y redundante con `python-dotenv`. Un evaluador que lea el
  `pyproject.toml` va a preguntar por qué hay un OCR instalado en un proyecto
  que usa GPT-4o Vision.

### Traza de referencia verificada en Langfuse — 2026-09-03

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

**Limitación conocida del set: ningún par elimina una cláusula entera.** Los
tres documentos enmendados conservan todas las cláusulas del original. La única
eliminación es interna (par 1, cláusula 1: desaparece "e intransferible"). El
Paso 3 pide distinguir adiciones, eliminaciones y modificaciones — con este set
la eliminación solo se demuestra a nivel de texto, no de cláusula. Decidir si se
agrega un par 4 o si se justifica la limitación en la defensa.

---

## 5. Decisiones que ya tomé yo

**`requirements.txt` descartado.** El profesor confirmó que `uv` +
`pyproject.toml` + `uv.lock` cumple el requisito de versiones fijadas. La
consigna lo pide igual; justificar el reemplazo en el README.

**`main.py` de la raíz borrado** — era el placeholder de `uv init`. El entry
point va en `src/main.py`.

---

## 6. Abierto — resolver con evidencia, no discutiendo

**`ContractChangeOutput` sin `Field(description=...)`.**
Decidí sacar las descriptions y mover las instrucciones de formato al system
prompt del `ExtractionAgent`. Riesgo conocido: la rúbrica 1.3 baja a
satisfactorio si *"faltan descripciones de campo"*.
Se resuelve empíricamente: correr el pipeline con y sin descriptions contra el
par 1 y comparar contra el ground truth de §4. Si el modelo normaliza la
numeración o inventa un cambio en la cláusula 6, vuelven los `Field`.
Esa comparación es material directo para el README.

**Chains (LCEL) vs `create_agent` para los dos agentes.** Ninguno de los dos
agentes tiene tools. Decidir y justificar en el README.

**Config del modelo hardcodeada en la llamada.** Decidí definir `"openai:gpt-4o"`,
`temperature`, `timeout` y `max_tokens` como literales dentro de
`init_chat_model()`, en vez de leerlos del `.env`. La API key sí sale de `.env`
(LangChain la toma sola de `os.environ`).
Riesgo conocido: la rúbrica 2.2 baja a satisfactorio con *"algunas claves o
configuraciones están hardcodeadas"*. Cuando existan los dos agentes, cada uno
va a instanciar su propio modelo — ahí se ve cuántos archivos hay que tocar para
cambiar de modelo, y si conviene volver atrás o centralizar en `src/config.py`.

**Nombres de spans. — RESUELTO 2026-09-03.**
`parse_contract_image()` corre dos veces con la misma función, pero los spans
tienen que llamarse distinto. Solución elegida: dos wrappers de una línea en
`main.py` (`_step_parse_original` / `_step_parse_amendment`), cada uno decorado
con `@observe(name=...)`. El nombre del span es responsabilidad del orquestador,
no del parser: `image_parser.py` no sabe cuál de los dos documentos está
procesando y no tiene por qué saberlo.

**El span raíz devuelve una tupla y ensucia el output de la traza.**
`run_contract_analysis()` está anotada `-> ContractChangeOutput` pero devuelve
`(contract_changes, trace_url)`. Dos consecuencias: (a) el type hint miente y un
type checker lo marcaría; (b) en Langfuse el output del span raíz se ve como un
array de dos elementos donde el segundo es la URL de la propia traza —
autorreferencial y ruidoso justo en el campo que la doc de Langfuse señala como
el más importante (es el que aparece en la tabla de trazas y el que leen los
evaluadores). Opción para arreglarlo: sacar el `get_trace_url()` de la función
decorada y llamarlo desde `main()` dentro de un `with lf_client.start_as_current_observation(...)`,
o simplemente dejar que `run_contract_analysis` devuelva solo el objeto Pydantic
y obtener la URL por separado.

**Dependencias muertas en `pyproject.toml`.** `pillow`, `pytesseract` y `dotenv`
(distinto de `python-dotenv`) no los importa ningún archivo. Decidir si se
borran antes de la entrega.

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
  `https://cloud.langfuse.com` (¡región EU!). Conviene renombrar la variable a
  `LANGFUSE_BASE_URL` en `.env` y `.env.example` antes de que el fallback
  desaparezca en una versión futura y las trazas se vayan silenciosamente a EU.
- El `CallbackHandler` no se configura con credenciales: llama a `get_client()`
  internamente y se engancha al span de OpenTelemetry que esté activo en ese
  momento. Por eso los spans de LangChain aparecen anidados bajo el `@observe`
  correspondiente sin que haya que pasarles ningún parent id.
- Un único `CallbackHandler()` alcanza para todo el pipeline: mantiene su estado
  por corrida en un dict indexado por UUID de run. Crear uno por etapa (como
  hace hoy `main.py`) funciona igual, pero no es necesario.
