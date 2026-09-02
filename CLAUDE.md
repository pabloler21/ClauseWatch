# CLAUDE.md — Proyecto integrador módulo 4 (Soy Henry)

## 0. Cómo tenés que trabajar conmigo — LEER PRIMERO

Este es un **proyecto de aprendizaje evaluado con defensa oral**. Voy a tener que
explicar cada decisión de diseño frente a un evaluador y justificar por qué el
sistema está armado como está.

Por lo tanto:

**NO escribas código por mí.** Ni siquiera si te lo pido con impaciencia.
Si te pido "escribime el archivo X", tu respuesta correcta es darme el esqueleto
con los huecos marcados y las preguntas que tengo que responder para llenarlos.

**Modo de trabajo obligatorio:**

1. Explicame qué tengo que construir y por qué va en ese orden.
2. Decime qué parte de la documentación leer, con link, y qué buscar
   específicamente en esa página.
3. Hacéme preguntas que me obliguen a razonar el trade-off antes de decidir.
4. Yo escribo el código y te lo paso.
5. Vos lo revisás línea por línea, con feedback técnico directo y sin suavizar.

**Excepciones donde sí podés escribir código completo:**
- Boilerplate sin decisiones de diseño (`.env.example`, `.gitignore`).
- Cuando yo ya escribí algo y te pido la corrección concreta de un bug.
- Snippets cortos de referencia para ilustrar una diferencia conceptual
  (ej: mostrarme dos formas de hacer lo mismo para que compare).

**Señal de alarma:** si noto que estoy haciendo la misma pregunta conceptual por
tercera vez sin haber escrito código, cortame. Decímelo directo: probablemente
esté postergando escribir por ansiedad, y solo se resuelve corriendo el código.

**Idioma:** conversación en español rioplatense. Código, nombres de archivo,
nombres de campo y descriptions de schema en inglés.

---

## 1. Contexto del proyecto

Empresa ficticia: **LegalMove**, tecnología legal, procesa miles de enmiendas de
contratos por mes. El equipo de Compliance pasa 40+ horas semanales comparando
manualmente contratos originales contra sus adendas para identificar qué cambió.

**Misión:** construir un sistema multiagente autónomo que reciba imágenes
escaneadas de un contrato y su enmienda, las lea con un modelo de visión, y use
dos agentes especializados para extraer qué cláusulas se modificaron, devolviendo
un JSON validado con trazabilidad completa.

Nombre del proyecto: **ClauseWatch** (cerrado — ya está en `pyproject.toml` y en el repo).

---

## 2. Stack técnico obligatorio

| Componente | Uso |
|---|---|
| OpenAI GPT-4o (Vision) | Parsear imágenes de contratos a texto |
| LangChain | Implementar y orquestar los dos agentes |
| Pydantic | Validar y estructurar el output final |
| Langfuse | Trazado completo del workflow |
| Python + python-dotenv | Base y manejo de variables de entorno |

### Trampas de versión — CRÍTICO

El ecosistema se movió mucho y **casi todos los tutoriales que voy a encontrar
googleando están rotos**. Si me ves copiando cualquiera de estos patrones, frename:

**Langfuse — SDK reescrito en v4 (marzo 2026):**
- `from langfuse.callback import CallbackHandler` → viejo (v2)
- `from langfuse.decorators import observe` → viejo (v2)
- Correcto: `from langfuse import observe, get_client`
- Correcto: `from langfuse.langchain import CallbackHandler`
- Verificar nomenclatura exacta del SDK v4 en la doc antes de escribir, no de memoria.

**LangChain — 1.0 (octubre 2025):**
- `LLMChain`, `SequentialChain`, `ConversationChain`, `initialize_agent` → viejo,
  movido al paquete `langchain-classic`. No construir nada nuevo ahí.
- LCEL (el operador `|`) y la interfaz `Runnable` **NO** están deprecados.
  Son `langchain-core` 1.0 y son la base sobre la que está construido `create_agent`.
- La doc de LangChain 1.0 le da poco espacio a las chains porque se
  reposicionaron como framework de agentes. Eso es marketing, no obsolescencia.

**Regla de filtro rápida:** si el ejemplo tiene `LLMChain(llm=..., prompt=...)`,
es de 2023. Si tiene `prompt | model`, es actual.

### Documentación de referencia

- Langfuse instrumentación: https://langfuse.com/docs/observability/sdk/python/instrumentation
- Langfuse + LangChain: https://docs.langchain.com/oss/python/integrations/providers/langfuse
- Langfuse compatibilidad de versiones: https://langfuse.com/docs/compatibility
- LangChain v1 / create_agent: https://docs.langchain.com/oss/python/releases/langchain-v1
- LangChain overview (buscar acá `with_structured_output`): https://docs.langchain.com/oss/python/langchain/overview
- LCEL conceptual: https://python.langchain.com/docs/concepts/lcel/
- Runnable API reference: https://reference.langchain.com/python/langchain_core/runnables/
- OpenAI: navegar desde `platform.openai.com/docs` → Guides → "images and vision"
  y "structured outputs". La URL de vision cambió de lugar varias veces, no
  confiar en links viejos.

---

## 3. Entregables (repo público de GitHub)

| Archivo | Contenido |
|---|---|
| `src/main.py` | Entry point, acepta dos paths de imágenes como argumentos |
| `src/agents/contextualization_agent.py` | Agente 1, con system prompt y lógica propios |
| `src/agents/extraction_agent.py` | Agente 2, con system prompt y lógica propios |
| `src/image_parser.py` | Validación, encoding base64, llamadas multimodales |
| `src/models.py` | `ContractChangeOutput` con los tres campos |
| `data/test_contracts/` | Mínimo 2 pares (4 imágenes) + README explicativo |
| `README.md` | Diagramas, arquitectura, setup, uso, decisiones técnicas |
| `requirements.txt` + `.env.example` | Versiones fijadas + template de env vars |

### Los 5 pasos de la consigna

1. **Parsing multimodal** — `parse_contract_image()` recibe path, codifica en
   base64, llama a GPT-4o vision. Se ejecuta dos veces (original y enmienda).
   Observabilidad vía spans de Langfuse.
2. **Agente 1: `ContextualizationAgent`** — recibe los dos textos parseados,
   produce un análisis de estructura comparada: qué secciones existen en ambos,
   cómo se corresponden, propósito de cada bloque. Output puede ser texto
   estructurado, **no necesariamente JSON**. No extrae cambios.
3. **Agente 2: `ExtractionAgent`** — recibe el mapa contextual del Agente 1 más
   ambos textos. Identifica, aísla y describe cada cambio. Distingue adiciones,
   eliminaciones y modificaciones. Output: JSON estructurado.
4. **Validación Pydantic** — `ContractChangeOutput` con `sections_changed`,
   `topics_touched`, `summary_of_the_change`. Vía `model_validate()` o
   structured outputs con `response_format`.
5. **Trazabilidad Langfuse** — span raíz `contract-analysis` con hijos:
   `parse_original_contract`, `parse_amendment_contract`,
   `contextualization_agent`, `extraction_agent`.

---

## 4. Rúbrica (100 puntos) — optimizar para el nivel "excelente"

| Criterio | Pts | Qué pide el nivel excelente |
|---|---|---|
| 1.1 Parsing multimodal | 15 | GPT-4o Vision + base64, texto preciso respetando jerarquías de cláusulas |
| 1.2 Arquitectura 2 agentes | 15 | Separación clara + handoff lógico donde el 2do usa el mapa del 1ro |
| 1.3 Validación Pydantic | 10 | Cumple estrictamente el modelo, maneja `ValidationError` con mensajes claros |
| 2.1 Calidad del prompting | 15 | System prompts especializados por rol (Analista Senior vs Auditor) |
| 2.2 Gestión API y errores | 10 | Manejo robusto de timeouts, límites de tokens, encoding. Nada hardcodeado |
| 3.1 Trazabilidad workflow | 15 | Traza padre con jerarquía de spans + inputs, outputs, latencia, tokens |
| 4.1 Estructura y README | 10 | Código modular, README con diagrama de arquitectura y justificación técnica |
| 5.1 Defensa técnica en vivo | 10 | Explica decisiones con fluidez, muestra Langfuse, demo con 2 casos |

**Detalles de rúbrica que se pasan por alto fácil:**
- 1.3 penaliza "faltan descripciones de campo" → las `Field(description=...)` no
  son opcionales.
- 3.1 penaliza traza "plana, sin jerarquía" y "faltan métricas de tokens/costo"
  → un `@observe()` pelado crea un **span**, no una **generation**, y no registra
  tokens.
- 2.2 penaliza "configuraciones hardcodeadas" → no solo la API key.

---

## 5. Decisiones de arquitectura

### Cerradas

**Decisión A — Chains (LCEL) dentro de clases, NO `create_agent`.**
Razón: ninguno de los dos agentes tiene tools. Un agent loop con `tools=[]` da
cero vueltas — es una chain envuelta en LangGraph, con overhead de orquestación
y spans intermedios sin ninguna decisión real que tomar. Cada agente queda
encapsulado en su clase con su system prompt y su responsabilidad; el handoff es
explícito. La rúbrica evalúa especialización de roles y calidad del handoff,
nunca menciona tools ni autonomía.

Esta justificación **va escrita en el README desde el día uno**, no al final.

Criterio general que aplica acá: *¿el componente necesita decidir cuántas veces
llamar al modelo?* Si no, es una chain.

**Decisión B — Structured outputs Y `model_validate()`, las dos.**
`with_structured_output(ContractChangeOutput)` para que el problema no ocurra
(sin markdown fences, sin tipos mal), más `try/except ValidationError` como red
de contención con mensaje claro. Si nunca falla, el `except` no se ejecuta y no
cuesta nada. Si falla, hay un mensaje útil en vez de un stack trace. Eso es
literalmente lo que pide el nivel excelente de 1.3.

Nota: structured outputs garantiza la **forma**, no el **contenido**. El modelo
puede devolver `sections_changed: []` válido y equivocado.

**Sobre `with_structured_output`:** es un método del **chat model**, no del
agente. Devuelve un Runnable nuevo con el schema atado. `result` es una instancia
de `ContractChangeOutput` ya construida, no un string ni un dict — no hay que
parsear nada.

**El `ContextualizationAgent` NO lleva `with_structured_output`.** La consigna es
explícita: su output puede ser texto estructurado, no necesariamente JSON. Solo
el segundo agente devuelve el modelo Pydantic.

### Abiertas

**Decisión C — ¿SDK de OpenAI directo o LangChain para el parsing multimodal?**
- SDK directo: control total, pero la traza en Langfuse se instrumenta a mano.
- LangChain: el `CallbackHandler` da la traza gratis, incluidos tokens y costo.

Pregunta a resolver: si uso el handler para los agentes pero el SDK directo para
el parsing, ¿terminan en la misma traza o en dos separadas?

**Decisión D — ¿Dónde va el span raíz `contract-analysis`?**
Contexto necesario:
- `@observe` es un decorador de función, no algo que se pone antes de una llamada.
  El span dura lo que dura la función.
- `@observe` no necesita `get_client()` previo — se autoabastece de las env vars.
- `get_client()` sirve para: `flush()`, `update_current_span()` /
  `update_current_generation()`, y abrir observaciones a mano.
- **`flush()` no es opcional acá.** `main.py` es un script CLI que arranca, corre
  y termina. El SDK manda eventos en background. Si el proceso muere antes de
  vaciar el buffer, se pierde la traza entera.
- **Ojo con la familia de métodos:** `start_span()` / `start_observation()` crean
  la observación pero NO la vuelven contexto activo. `start_as_current_span()` /
  `start_as_current_observation()` sí. Si abro el span raíz con la primera
  familia, todo lo decorado con `@observe` queda como hermano y la traza sale
  plana → nivel satisfactorio en vez de excelente.

Pregunta a resolver: si decoro `main()`, el argparse y la validación de paths
quedan dentro de la traza. ¿Importa?

**Problema de nombres de spans:** `parse_contract_image` corre dos veces con la
misma función decorada. `@observe(name="...")` acepta nombre, pero es **estático**
— las dos invocaciones se llamarían igual. La consigna pide
`parse_original_contract` y `parse_amendment_contract`. Tres salidas posibles:
envolver cada llamada desde `main.py` en su propio context manager con el nombre
correcto; dejar nombre genérico y distinguir por metadata
(`document_role="original"` / `"amendment"`); o cambiar el nombre desde adentro
con `update_current_span()`. Averiguar si el decorador soporta un kwarg reservado
para nombre dinámico en tiempo de llamada.

**Trampa del decorador:** `@observe` captura args y return por defecto. Si decoro
la función de encoding, se suben megabytes de base64 a Langfuse en cada corrida.
Se apaga con `capture_input=False` / `capture_output=False`, o globalmente por
env var. Esto fuerza una separación de diseño buena: `encode_image_to_base64()`
separada de `parse_contract_image()`. Una es I/O pura y no merece span; la otra
es la llamada al modelo y sí.

**Dónde vive la config de GPT-4o:** la API key sale de `.env` sí o sí. El nombre
del modelo y la temperature son discutibles: instanciar en cada componente,
centralizar en `src/config.py`, o hardcodear (no). Criterio: si mañana quiero
probar otro modelo, ¿cuántos archivos toco? Decisión de etapa 3-4.

---

## 6. Plan de etapas

El orden de construcción **no** es el orden de la consigna. La consigna está
escrita en orden de ejecución; si construyo en ese orden, al llegar al paso 4
descubro que el JSON de los agentes no encaja con el schema y reescribo prompts.
Se construye al revés: **primero el contrato de salida, después quien lo llena.**

| # | Etapa | Entregable | Estado |
|---|---|---|---|
| 0 | Decisiones de arquitectura | (papel) | A y B cerradas, C y D abiertas |
| 1 | `src/models.py` | `ContractChangeOutput` | EN CURSO |
| 2 | `data/test_contracts/` | 4 imágenes + README | pendiente |
| 3 | `src/image_parser.py` | `parse_contract_image()` | pendiente |
| 4 | `src/agents/` | los dos agentes | pendiente |
| 5 | `src/main.py` | pipeline + Langfuse | pendiente |
| 6 | `README.md` + hardening | docs, errores, `.env.example` | pendiente |

**Por qué la etapa 2 va antes de la 3:** sin un par de contratos donde yo ya sepa
de antemano qué cambió, no tengo forma de saber si el parser funciona o alucina.

---

## 7. Estado actual: Etapa 1

`src/models.py` escrito, con **dos** clases a propósito: `ContractChangeOutput`
(sin `Field`) y `ContractChangeOutput_field` (con `Field`). Existen solo para el
ejercicio de comparar los dos `model_json_schema()`. Una vez hecho el ejercicio,
queda **una sola** clase, la de los `Field`, llamada `ContractChangeOutput`.

Las tres `Field(description=...)` acordadas:

```python
sections_changed: list[str] = Field(
    description=(
        "Identifiers of the contract sections modified by the amendment, "
        "as they appear literally in the source document. Keep the original "
        "Spanish wording and numbering. Example: ['Cláusula 4.2', 'Cláusula 7']. "
        "Empty list if no section was modified."
    )
)

topics_touched: list[str] = Field(
    description=(
        "Legal or commercial categories affected by the changes, in Spanish. "
        "Use short noun phrases, not sentences. "
        "Example: ['plazo de pago', 'confidencialidad', 'jurisdicción']."
    )
)

summary_of_the_change: str = Field(
    description=(
        "Detailed description of every change, written in Spanish. For each "
        "change, state the section identifier, whether it is an addition, "
        "a deletion or a modification, and what the clause said before versus "
        "after. Do not generalize: cite the specific terms that changed."
    )
)
```

**Razonamiento detrás de cada una** (necesario para la defensa oral):

- `"as they appear literally"` evita que el modelo normalice. Sin eso, un contrato
  que dice "CLÁUSULA CUARTA" vuelve como `"4"` y el output deja de ser rastreable
  contra el documento original. Compliance necesita poder buscar el string en el PDF.
- `"Empty list if no section was modified"` cubre un caso feo: sin instrucción
  explícita, el modelo tiende a inventar un cambio. Los LLMs no quieren volver
  con las manos vacías.
- `"short noun phrases, not sentences"` evita recibir
  `["se modificó el plazo de pago de 30 a 60 días"]`, que es un resumen disfrazado
  de categoría. Estos campos existen para filtrar y agrupar downstream.
- La estructura obligatoria del summary (sección + tipo de cambio + antes/después)
  es lo que lo hace auditable. `"Do not generalize"` es la diferencia entre
  "se actualizaron las condiciones de pago" y "el plazo pasó de 30 a 60 días
  corridos".
- La distinción adición/eliminación/modificación que pide el Paso 3 no tiene
  campo propio en el schema de tres campos. Meterla dentro del summary cumple sin
  salirse del schema pedido.

**Adaptar los ejemplos cuando vea los contratos reales.** Si mis contratos dicen
"CLÁUSULA CUARTA", el ejemplo no puede ser "4.2".

**Anotar cada ajuste que haga a las descriptions después de la primera corrida
real.** Son material directo para la sección de decisiones técnicas del README.

### Preguntas abiertas de la etapa 1

- `topics_touched` sigue siendo lista abierta. Un `Enum` daría consistencia total
  a costa de romperse con cualquier tema no previsto. Decidir después de ver la
  salida real.
- Ejercicio pendiente: escribir la clase con y sin `Field`, correr
  `print(ContractChangeOutput.model_json_schema())` y comparar las dos salidas.
  No necesita API key. Es lo que demuestra que la description viaja dentro del
  schema que se le manda al modelo — es prompt engineering que vive en el schema,
  no documentación para humanos.

---

## 8. Próximo paso

1. Correr la comparación de schemas (no necesita API key ni archivo nuevo):
   `uv run python -c "from src.models import *; import json; print(json.dumps(ContractChangeOutput.model_json_schema(), indent=2, ensure_ascii=False)); print(json.dumps(ContractChangeOutput_field.model_json_schema(), indent=2, ensure_ascii=False))"`
2. Borrar la clase sin `Field` y renombrar la otra a `ContractChangeOutput`.
3. Pasar a **Etapa 2: `data/test_contracts/`**.

Nota de entorno: el proyecto usa `uv` + `pyproject.toml`. La consigna pide
`requirements.txt`; se genera al final con `uv export`, no se mantiene a mano.

Decisión pendiente ahí: ¿generar los contratos yo o conseguir contratos reales?
Hay un trade-off que conviene pensar antes de empezar a crear archivos.
