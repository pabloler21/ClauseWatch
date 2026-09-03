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

## 4. Estado real del repo — verificado 2026-09-02

```
CLAUDE.md          consigna.md        pyproject.toml     uv.lock
.env (ignorado)    .env.example       .gitignore         README.md (vacío)
src/models.py
data/test_contracts/   6 imágenes = 3 pares
```

**Hecho:**
- `src/models.py` — `ContractChangeOutput` con los 3 campos y docstring de clase.
  Sin `Field(description=...)`. Ver §6.
- 3 pares de contratos de prueba en `data/test_contracts/` (la consigna pide
  mínimo 2), nombrados `documento_N_original.jpg` / `documento_N_enmienda.jpg`
  — el número del par va primero para que al ordenar queden los pares juntos.
  **Falta el README explicativo de esa carpeta**, que la consigna pide como
  parte del entregable.
- Entorno: `uv` + `pyproject.toml`. Instalado: `langchain 1.3.18`,
  `langchain-openai 1.6.0`, `pydantic 2.13.5`, `python-dotenv 1.2.3`.
- `.env` creado y gitignoreado. `.env.example` como template.

**Falta:** `src/image_parser.py`, `src/agents/` (los dos), `src/main.py`,
Langfuse (ni instalado), `README.md` raíz.

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

**Nombres de spans.** `parse_contract_image()` corre dos veces con la misma
función, pero los spans tienen que llamarse `parse_original_contract` y
`parse_amendment_contract`. Verificar en la doc de Langfuse cómo se hace.

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

**Pendiente de verificar antes de escribir una línea de Langfuse:** el SDK tuvo
una reescritura mayor y los imports cambiaron. No escribir nada de Langfuse de
memoria — traer la doc primero.
