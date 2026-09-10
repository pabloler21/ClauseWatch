# `EXTRACTION_SYSTEM_PROMPT`

**Agente 2 — ExtractionAgent** · Paso 3 y 4 del pipeline
Definido en [`src/agents/extraction_agent.py`](../../src/agents/extraction_agent.py)

Rol: **Auditor Legal Senior de Compliance**. Recibe los dos textos parseados más el
mapa estructural del Agente 1, y extrae cada cambio introducido por la enmienda.
Su salida se valida contra `ContractChangeOutput` (Pydantic) vía
`with_structured_output()`.

| Versión | Fecha | Commit | Estado |
|---|---|---|---|
| [v1](#v1) | 2026-09-03 | `bd20aa3` | reemplazada |
| [v2](#v2) | 2026-09-10 | `ddd2b53` | reemplazada |
| [v3](#v3) | 2026-09-10 | sin commitear | **viva** |

---

<a name="v1"></a>
## v1 — 2026-09-03 — `bd20aa3`

Primera versión. Escrita junto con el agente.

### Decisiones de diseño

- **Rol especializado y contrastante con el Agente 1.** "Senior Legal Compliance
  Auditor" contra "Senior Legal Contract Analyst". La rúbrica 2.1 pide
  literalmente *"system prompts altamente especializados por rol (Analista Senior
  vs Auditor)"*.
- **Las tres dimensiones explícitas** (Modifications / Additions / Deletions),
  porque el Paso 3 de la consigna pide distinguirlas.
- **Instrucciones de formato por campo dentro del prompt**, en vez de
  `Field(description=...)` en `models.py`. Decisión registrada en `CLAUDE.md` §6.
- **Regla anti-ruido**: *"Do not report changes for clauses that are identical"*.
  Existe por la cláusula 6 del par 1, que es idéntica en ambos documentos y es la
  trampa del set de prueba.

### Texto completo

```text
You are a Senior Legal Compliance Auditor specializing in contractual change extraction.

Your sole responsibility is to rigorously compare an original contract against its amendment, guided by the provided structural alignment map, and extract every legal and commercial modification introduced.

You must categorize and evaluate all alterations across three dimensions:
1. Modifications: Alterations to terms, deadlines, prices, percentages, or conditions within existing clauses.
2. Additions: Entirely new clauses or provisions introduced in the amendment that were absent in the original.
3. Deletions: Clauses or specific wording present in the original that were removed or suppressed in the amendment.

Instructions for populating the output fields:
- `sections_changed`: List the exact section/clause identifiers that experienced any modification, addition, or deletion (e.g., ["1. Otorgamiento de Licencia", "2. Plazo"]). Do NOT include sections that remained completely unchanged.
- `topics_touched`: List the distinct legal and commercial domains affected by the changes (e.g., ["Licencia y alcance", "Vigencia del contrato", "Tarifas y pagos", "Soporte técnico", "Plazos de rescisión", "Protección de datos"]).
- `summary_of_the_change`: Write a comprehensive, objective audit summary in Spanish detailing each identified change. For each affected clause, explicitly state what was modified, added, or deleted, quoting or citing specific values (e.g., amounts, timeframes, or specific wording differences).

CRITICAL RULES:
- Ground all findings strictly on the provided texts and structural map. Do not speculate or hallucinate.
- Do not report changes for clauses that are identical between both documents.
- Write the summary and topic names in Spanish.
```

### Resultado medido

Traza `b42c5ab8f1c320f4a710e7c6f1fde5ef` (par 1, 2026-09-10).

**Lo que funcionó:**

- `sections_changed` = las 6 correctas, **sin** `6. Confidencialidad`. No cayó en
  la trampa.
- Valores concretos citados bien: `12 → 24 meses`, `USD 12.000 → USD 15.000`,
  `30 → 60 días`.
- Distinguió la cláusula 7 como adición.
- Costo: 1.511 prompt → 345 completion, **$0.007227**.

**Lo que falló — el motivo del cambio a v2:**

El par 1, cláusula 1 contiene **tres** cambios:

| # | Cambio | Tipo |
|---|---|---|
| 1 | Desaparece `e intransferible` | eliminación |
| 2 | Desaparece `únicamente` | eliminación |
| 3 | `para fines internos de la empresa` → `para operaciones internas de negocio` | modificación |

Lo que reportó v1:

> *"1. Otorgamiento de Licencia: Se modificó el alcance de la licencia otorgada.
> En el contrato original, la licencia era para 'fines internos de la empresa',
> mientras que en la enmienda se especifica que es para 'operaciones internas de
> negocio'."*

**Capturó solo la reformulación. Perdió las dos eliminaciones.**

`e intransferible` es la **única eliminación de todo el set de datos** (ver la
sección "Limitación conocida" del ground truth). Con v1, el pipeline demostraba
adiciones y modificaciones, y eliminaciones **0 de 1** — incumpliendo la mitad del
Paso 3 de la consigna.

Además es el cambio jurídicamente más grave del documento: quitar "intransferible"
habilita al Licenciatario a ceder la licencia a un tercero. v1 reportó el cambio
cosmético y perdió el sustantivo.

**Descartado como causa:**

- El parsing conserva `e intransferible`, `únicamente`, la numeración de cláusulas
  y los montos sin normalizar. Verificado ejecutando `src/image_parser.py` sobre
  `documento_1_original.jpg`.
- El Agente 1 no interviene: su prompt le prohíbe extraer cambios.
- El Agente 2 recibió los 1.511 tokens con ambos textos completos y el mapa.

→ La causa estaba en este prompt.

---

<a name="v2"></a>
## v2 — 2026-09-10 — sin commitear

### Qué cambió

| # | Dónde | v1 | v2 |
|---|---|---|---|
| 1 | frase de misión | *"extract every legal and commercial **modification**"* | *"…every legal and commercial **change**"* — `modification` era una de las tres categorías usada como término paraguas de las tres |
| 2 | dimensión "Deletions" | *"Clauses or specific wording … removed or suppressed"* | agrega el caso intra-cláusula explícito, con ejemplo: un calificativo que cae de una cláusula que por lo demás sobrevive |
| 3 | **bloque nuevo** | — | `Comparison procedure`: leer frase por frase, listar cada diferencia por separado, recién después redactar |
| 4 | `summary_of_the_change` | *"**For each affected clause**, explicitly state what was modified, added, or deleted"* | *"Report **each individual change** separately … a clause holding three changes must produce three statements, not one"* |
| 5 | CRITICAL RULES | — | regla nueva: los calificativos legales que definen alcance, si desaparecen, son eliminación y nunca reescritura de estilo |
| 6 | CRITICAL RULES | regla anti-ruido | **intacta** — es la que protege la cláusula 6 |

**El cambio decisivo fue el #4.** `summary_of_the_change` estaba definido a nivel
*cláusula*, no a nivel *cambio*. Eso producía el formato observado — un ítem por
cláusula — y una vez que el modelo abría el ítem "1. Otorgamiento de Licencia" y lo
etiquetaba "se modificó el alcance", el ítem quedaba cerrado. No había dónde poner
el segundo ni el tercer cambio de esa cláusula.

### Nota metodológica — el ejemplo no contamina el test

El ejemplo de la dimensión "Deletions" usa **`irrevocable e incondicional`**, no
`e intransferible`. La lista de calificativos de CRITICAL RULES nombra
`exclusiva`, `irrevocable`, `incondicional`, `perpetua`, `solidaria` — y
deliberadamente **no** `intransferible` ni `únicamente`.

Si el prompt nombrara la palabra que el test busca, el test mediría "¿el modelo
sigue una instrucción literal?" en vez de "¿el modelo detecta eliminaciones?".
Al usar un calificativo análogo pero distinto, que el modelo encuentre
`intransferible` demuestra que generalizó la categoría.

### Texto completo

```text
You are a Senior Legal Compliance Auditor specializing in contractual change extraction.

Your sole responsibility is to rigorously compare an original contract against its amendment, guided by the provided structural alignment map, and extract every legal and commercial change introduced.

You must categorize and evaluate all alterations across three dimensions:
1. Modifications: Alterations to terms, deadlines, prices, percentages, or conditions within existing clauses.
2. Additions: Entirely new clauses or provisions introduced in the amendment that were absent in the original.
3. Deletions: Any wording present in the original and absent from the amendment. This covers an entire clause that disappears AND — just as importantly — a single word, adjective or qualifier dropped from a clause that otherwise survives. For example, a guarantee described as "irrevocable e incondicional" in the original and only as "irrevocable" in the amendment: "e incondicional" was deleted, and that is a finding.

Comparison procedure — apply it to every pair of corresponding clauses:
1. Read the original clause and the amended clause phrase by phrase.
2. List every difference separately, however small: wording added, wording removed, and values altered are three distinct findings even when they occur inside the same clause.
3. Only after listing them individually, write them into the summary.
A single clause frequently contains more than one change of more than one type. Reporting only the most visible one is an incomplete audit.

Instructions for populating the output fields:
- `sections_changed`: List the exact section/clause identifiers that experienced any modification, addition, or deletion (e.g., ["1. Otorgamiento de Licencia", "2. Plazo"]). Do NOT include sections that remained completely unchanged. A clause is listed once, however many changes it contains.
- `topics_touched`: List the distinct legal and commercial domains affected by the changes (e.g., ["Licencia y alcance", "Vigencia del contrato", "Tarifas y pagos", "Soporte técnico", "Plazos de rescisión", "Protección de datos"]).
- `summary_of_the_change`: Write a comprehensive, objective audit summary in Spanish. Report each individual change separately, quoting the specific values or wording involved (amounts, timeframes, deleted expressions). Group the entries by clause, but a clause holding three changes must produce three statements, not one. State explicitly for each one whether it is a modificación, an adición or an eliminación.

CRITICAL RULES:
- Ground all findings strictly on the provided texts and structural map. Do not speculate or hallucinate.
- Do not report changes for clauses that are identical between both documents.
- Legal qualifiers such as "exclusiva", "irrevocable", "incondicional", "perpetua" or "solidaria" define the scope of a right or an obligation. If one of them is present in the original and missing from the amendment, report it as an eliminación: it is a substantive change, never a stylistic rewording.
- Write the summary and topic names in Spanish.
```

### Resultado medido

Tres corridas, una por par.

#### Par 1 — traza `9f6a0d906db6fb5d0920e9d4a82cf657`

| Test | Criterio | Resultado |
|---|---|---|
| T1 | ¿aparece `intransferible`? | ✅ **SÍ** |
| T2 | ¿`únicamente` como eliminación? | ⚠️ no (era deseable, no bloqueante) |
| T3 | `sections_changed` | ✅ las 6 exactas |
| T4 | ¿aparece `6. Confidencialidad`? | ✅ **NO** — sin sobre-corrección |
| T5 | valores concretos | ✅ `12→24`, `12.000→15.000`, `30→60` |
| T6 | cláusula 7 | ✅ etiquetada `Adición` |

Salida de la cláusula 1:

```
1. Otorgamiento de Licencia:
- Eliminación: Se eliminó la palabra "intransferible" de la descripción de la
  licencia, cambiando el alcance de la misma.
- Modificación: Se cambió "fines internos de la empresa" por "operaciones
  internas de negocio".
```

**Efecto secundario no planificado:** el formato de salida cambió solo. Cada ítem
viene ahora etiquetado `Eliminación:` / `Modificación:` / `Adición:`. La distinción
de los tres tipos que pide el Paso 3 quedó legible en el output **sin tocar el
schema Pydantic**.

#### Par 2 — traza `809d66f294c1a5d1fc85176f668b46c9`

`sections_changed` = `1, 2, 3, 4, 7`. ✅ 5/5, sin las cláusulas 5 ni 6 (las dos
idénticas).

Clasificaciones: 5/5 correctas, incluido el caso que el ground truth marca como la
trampa conceptual — *"El cambio en la 1 es una adición dentro de una cláusula
existente, no una cláusula nueva. La distinción importa: es una modificación, no
una adición."*

Salida: *"1. Alcance del Servicio: Se ha añadido 'y análisis regulatorio' al
alcance de los servicios de consultoría. **Esto es una modificación**."* ✅

#### Par 3 — traza `dcb30ef887c62a1860b9f0dd19143a89`

Control anti-ruido: sin adiciones, cláusulas 1 y 2 idénticas.

| Test | Criterio | Resultado |
|---|---|---|
| T7 | `sections_changed` | ✅ `3. Precio`, `4. Disponibilidad del Servicio`, `5. Soporte` |
| T8 | ¿aparecen las cláusulas 1 o 2? | ✅ **NO** |
| T9 | tipo de la cláusula 5 | ❌ dice `adición`; el ground truth dice **modificación** |
| T10 | valores | ✅ `1.200→1.250`, `99,5%→99,9%` |

#### Costo

Comparación del GENERATION de `extraction_agent`, par 1, v1 contra v2:

| Métrica | v1 | v2 | Δ |
|---|---|---|---|
| Prompt | 1.511 | 1.756 | **+245** (+16 %) |
| Completion | 345 | 309 | **−36** (−10 %) |
| Costo del agente | $0.007227 | $0.007480 | +$0.00025 |
| **Costo total de la traza** | **$0.025672** | **$0.025635** | **−$0.00004** |

El prompt más largo se paga solo: la salida estructurada resulta más concisa que
la prosa de v1. La corrida completa salió marginalmente **más barata** que con v1.

### Fallo detectado — inconsistencia adición / modificación

T9 expuso un problema que v2 no resuelve: la clasificación de texto **agregado
dentro de una cláusula existente** es inestable entre corridas.

| Caso | Cambio | v2 clasificó | Ground truth |
|---|---|---|---|
| Par 1, cl. 4 | email → email **y chat** | modificación ✅ | modificación |
| Par 2, cl. 1 | agrega "y análisis regulatorio" | modificación ✅ | modificación |
| Par 3, cl. 5 | email → email **y tickets** | **adición** ❌ | modificación |

2 de 3 correctos, mismo tipo de caso. No es un error sistemático: es
inestabilidad.

**Causa:** la dimensión "Additions" decía *"Entirely new clauses **or
provisions**"*. Ese `or provisions` es ambiguo — un método de soporte agregado se
puede leer como una "provision" nueva. La frontera que el ground truth marca
explícitamente no estaba en el prompt.

→ Resuelto en [v3](#v3).

---

<a name="v3"></a>
## v3 — 2026-09-10 — sin commitear

### Qué cambió

Una sola línea, la dimensión "Additions":

| | Texto |
|---|---|
| **v2** | `2. Additions: Entirely new clauses `**`or provisions`**` introduced in the amendment that were absent in the original.` |
| **v3** | `2. Additions: Entirely new clauses introduced in the amendment that were absent in the original. `**`Wording added inside a clause that already existed in the original is a modification of that clause, never an addition.`** |

Dos ediciones en una: se elimina el `or provisions` ambiguo y se agrega la regla
de frontera explícita. El resto del prompt queda idéntico a v2.

### Texto completo

Idéntico a [v2](#v2) salvo la línea 2 de "three dimensions", que pasa a ser:

```text
2. Additions: Entirely new clauses introduced in the amendment that were absent in the original. Wording added inside a clause that already existed in the original is a modification of that clause, never an addition.
```

### Resultado medido

Tres corridas, una por par.

| Par | Traza |
|---|---|
| 1 | `01ceeae05e3d4363ecbf6659e9a0c991` |
| 2 | `af5c7bcfbd66058a430205a5e3ec110e` |
| 3 | `fd2653e52a837c8567888a5d1e393fee` |

#### El caso objetivo — T9 resuelto

| Caso | Cambio | v2 | **v3** | Ground truth |
|---|---|---|---|---|
| Par 1, cl. 4 | email → email y chat | modificación ✅ | **modificación** ✅ | modificación |
| Par 2, cl. 1 | agrega "y análisis regulatorio" | modificación ✅ | **modificación** ✅ | modificación |
| Par 3, cl. 5 | email → email y tickets | adición ❌ | **modificación** ✅ | modificación |

**3 de 3.** Par 3: *"5. Soporte: **Modificación** en los métodos de soporte al
cliente, añadiendo el sistema de tickets en línea al soporte vía correo
electrónico existente."*

#### No-regresión — las adiciones reales siguen siendo adiciones

El riesgo del fix era sobre-corregir en el otro sentido y empezar a llamar
"modificación" a cláusulas enteramente nuevas.

| Caso | v3 clasificó | Ground truth |
|---|---|---|
| Par 1, cl. 7 (Protección de Datos) | **adición** ✅ | adición |
| Par 2, cl. 7 (Propiedad Intelectual) | **adición** ✅ | adición |

`sections_changed` sin cambios respecto de v2 en los tres pares: 6/6, 5/5 y 3/3,
sin las cláusulas idénticas (par 1 cl. 6; par 2 cl. 5 y 6; par 3 cl. 1 y 2).

#### Mejora no buscada — la cláusula 1 del par 1 se abrió en dos entradas

v2 producía una entrada con dos hechos adentro. v3 emite dos entradas separadas,
cada una con su tipo:

```
1. Otorgamiento de Licencia: Se eliminó la palabra "intransferible" de la
   descripción de la licencia, lo que constituye una eliminación.
1. Otorgamiento de Licencia: Se modificó el uso permitido del software de
   "fines internos de la empresa" a "operaciones internas de negocio", lo que
   constituye una modificación.
```

Es el `Comparison procedure` de v2 funcionando de lleno: una cláusula, dos
findings, dos tipos distintos. Y `sections_changed` la lista una sola vez, como
pide la instrucción del campo.

#### Costo

| Métrica | v2 par 1 | v3 par 1 | v2 par 3 | v3 par 3 |
|---|---|---|---|---|
| Prompt | 1.756 | 1.804 | 1.388 | 1.406 |
| Completion | 309 | 327 | 166 | 143 |
| Costo del agente | $0.007480 | $0.007780 | $0.005130 | $0.004945 |
| Costo total de la traza | $0.025635 | $0.026195 | $0.018930 | $0.018715 |

El texto agregado al system prompt son ~20 tokens. El delta observado varía
(+48 en el par 1, +18 en el par 3) porque el user prompt incluye el mapa del
Agente 1, que cambia de corrida a corrida: el delta medido no es puro.

En completion el efecto va en las dos direcciones: el par 1 sube (+18) porque la
cláusula 1 ahora produce dos entradas en vez de una, y el par 3 baja (−23) porque
la redacción quedó más compacta. En plata: ±$0.0003 por corrida, ruido.

### Pendiente abierto

Ninguno derivado de v3. Queda en pie la decisión, ahora sin urgencia, de agregar
un campo `changes: list[ClauseChange]` con
`change_type: Literal["addition", "deletion", "modification"]` a
`ContractChangeOutput`: v3 produce la clasificación correcta 3 de 3, pero sigue
viviendo en prosa y por lo tanto no es consultable por máquina. Decisión
registrada como abierta en `CLAUDE.md` §6.
