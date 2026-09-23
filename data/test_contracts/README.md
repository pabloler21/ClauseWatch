# Contratos de prueba — ground truth

Tres pares de contratos sintéticos (original + enmienda) usados para validar el
pipeline. Cada par está en formato imagen (JPEG), que es la entrada real del
sistema: `parse_contract_image()` los lee con GPT-4o Vision.

**Para qué existe este archivo:** es el ground truth. Sin él no hay forma de
distinguir "el pipeline funciona" de "el pipeline devolvió algo verosímil".
Un LLM siempre va a devolver algo que *parece* un análisis de contrato. Lo que
sigue es contra qué se compara esa salida.

Los cambios de abajo se leyeron de las imágenes a mano, **antes** de correr
ningún modelo.

---

## Inventario

| Par | Archivos | Tipo de contrato | Cláusulas (orig → enm) |
|---|---|---|---|
| 1 | `documento_1_original.jpg` / `documento_1_enmienda.jpg` | Licencia de software (TechNova / DataBridge) | 6 → 7 |
| 2 | `documento_2_original.jpg` / `documento_2_enmienda.jpg` | Servicios de consultoría (Orion / GreenWave) | 6 → 7 |
| 3 | `documento_3_original.jpg` / `documento_3_enmienda.jpg` | Servicio SaaS (CloudMetrics / RetailPulse) | 5 → 5 |
| — | `documento_4_original.jpg`, `documento_1_enmienda_cesion.jpg` | Solo para el chequeo de correspondencia (ver abajo) | — |

Los tres usan numeración `N. Título`. Las tipografías difieren entre pares
(pares 1 y 2 en sans serif, par 3 en serif), lo que da algo de variedad para
probar la fidelidad del parsing multimodal.

---

## Par 1 — Contrato de Licencia de Software

`TechNova S.A.` (Licenciante) y `DataBridge Soluciones S.R.L.` (Licenciatario),
celebrado el 1 de marzo de 2024.

| Cláusula | Tipo | Cambio |
|---|---|---|
| 1. Otorgamiento de Licencia | modificación | Cae "e intransferible". "únicamente para fines internos de la empresa" → "para operaciones internas de negocio" |
| 2. Plazo | modificación | 12 → 24 meses |
| 3. Pago | modificación | USD 12.000 → USD 15.000 anuales (los 30 días de plazo no cambian) |
| 4. Soporte | modificación | correo electrónico → correo electrónico **y chat** |
| 5. Terminación | modificación | preaviso de 30 → 60 días |
| 6. Confidencialidad | **sin cambios** | — |
| 7. Protección de Datos | **adición** | Cláusula nueva, no existe en el original |

**Total:** 5 modificaciones, 1 adición, 1 sin cambios.

Casos interesantes de este par:
- La cláusula 6 es idéntica en ambos documentos. Es la trampa: un modelo que
  quiere "encontrar algo" va a reportarla igual.
- La cláusula 1 tiene una eliminación *dentro* de la cláusula (desaparece "e
  intransferible") junto con una reformulación. Requiere leer la redacción, no
  solo comparar títulos.
- La cláusula 3 cambia el monto pero no el plazo de pago. Un resumen perezoso
  diría "cambiaron las condiciones de pago" y perdería cuál de las dos.

---

## Par 2 — Contrato de Servicios de Consultoría

`Orion Consulting Group` (Consultor) y `GreenWave Energía S.A.` (Cliente),
celebrado el 10 de enero de 2024.

| Cláusula | Tipo | Cambio |
|---|---|---|
| 1. Alcance del Servicio | modificación | Agrega "y análisis regulatorio" al final |
| 2. Duración | modificación | 6 → 9 meses |
| 3. Honorarios | modificación | USD 8.000 → USD 9.500 mensuales |
| 4. Entregables | modificación | reportes **mensuales** → **quincenales** de avance |
| 5. Confidencialidad | **sin cambios** | — |
| 6. Legislación Aplicable | **sin cambios** | — |
| 7. Propiedad Intelectual | **adición** | Cláusula nueva, no existe en el original |

**Total:** 4 modificaciones, 1 adición, 2 sin cambios.

Casos interesantes de este par:
- Dos cláusulas consecutivas sin cambios (5 y 6). Prueba que el sistema no
  reporta ruido.
- El cambio en la 1 es una adición *dentro* de una cláusula existente, no una
  cláusula nueva. La distinción importa: es una modificación, no una adición.
- El cambio en la 4 es de una sola palabra (`mensuales` → `quincenales`) y
  cambia la obligación al doble de frecuencia. Es el caso donde un resumen
  genérico pierde toda la información útil.

---

## Par 3 — Contrato de Servicio SaaS

`CloudMetrics Ltd.` (Proveedor) y `RetailPulse S.A.` (Cliente), celebrado el
1 de febrero de 2024.

| Cláusula | Tipo | Cambio |
|---|---|---|
| 1. Servicio | **sin cambios** | — |
| 2. Plazo de Suscripción | **sin cambios** | — |
| 3. Precio | modificación | USD 1.200 → USD 1.250 mensuales |
| 4. Disponibilidad del Servicio | modificación | 99,5% → 99,9% |
| 5. Soporte | modificación | correo electrónico → correo electrónico **y sistema de tickets en línea** |

**Total:** 3 modificaciones, 2 sin cambios. Sin adiciones.

Casos interesantes de este par:
- **El documento no se titula "ENMIENDA" sino "VERSIÓN ACTUALIZADA".** No es una
  adenda que modifica, es el contrato completo reescrito. El
  `ContextualizationAgent` tiene que darse cuenta igual de que se corresponde
  con el original.
- Es el par con los cambios más chicos: 1.200 → 1.250 y 99,5% → 99,9%. Un dígito
  de diferencia. Si el parsing multimodal transcribe mal un número, el error
  aparece acá.
- Ninguna cláusula nueva. Sirve como control de que el sistema no inventa
  adiciones.

---

## Casos de correspondencia

El pipeline verifica, antes de correr los agentes, que las dos imágenes sean el
mismo contrato (`src/document_match.py`). Si no lo son, cualquier "cambio" que
reportara el Agente 2 sería inventado. Estos casos prueban ese chequeo, y la
tabla de veredictos esperados se escribió **antes** de correr ningún modelo.

Dos imágenes existen solo para este chequeo (no tienen tabla de cambios):

| Archivo | Qué es | Por qué existe |
|---|---|---|
| `documento_4_original.jpg` | Acuerdo de Confidencialidad entre **las mismas partes del par 1** (TechNova / DataBridge), 15 de enero de 2024 | **Negativo difícil.** Un filtro que solo mira las partes lo dejaría pasar como enmienda del par 1 |
| `documento_1_enmienda_cesion.jpg` | Enmienda N.º 2 del par 1, donde DataBridge cedió su posición a **Nexa Data Systems S.A.** | **Positivo difícil.** Cambia una parte y sigue siendo el mismo contrato. Un filtro "¿mismas partes?" lo rechazaría |

Las dos se generaron con un script de Pillow fuera del repo, imitando el formato
de los pares 1 a 3 (1242×1755 px, Arial).

### Veredictos esperados — 11 casos

| # | Original | Segundo documento | Esperado | Por qué |
|---|---|---|---|---|
| 1 | `documento_1_original` | `documento_1_enmienda` | ✅ mismo contrato | par válido |
| 2 | `documento_2_original` | `documento_2_enmienda` | ✅ mismo contrato | par válido |
| 3 | `documento_3_original` | `documento_3_enmienda` | ✅ mismo contrato | par válido; la enmienda se titula "VERSIÓN ACTUALIZADA" |
| 4 | `documento_1_original` | `documento_2_enmienda` | ❌ distinto | otras partes, otro objeto |
| 5 | `documento_1_original` | `documento_3_enmienda` | ❌ distinto | otras partes, otro objeto |
| 6 | `documento_2_original` | `documento_1_enmienda` | ❌ distinto | otras partes, otro objeto |
| 7 | `documento_2_original` | `documento_3_enmienda` | ❌ distinto | otras partes, otro objeto |
| 8 | `documento_3_original` | `documento_1_enmienda` | ❌ distinto | otras partes, otro objeto |
| 9 | `documento_3_original` | `documento_2_enmienda` | ❌ distinto | otras partes, otro objeto |
| 10 | `documento_4_original` | `documento_1_enmienda` | ❌ distinto | **mismas partes**, otro contrato (la enmienda cita un contrato de licencia del 1 de marzo, no un NDA del 15 de enero) |
| 11 | `documento_1_original` | `documento_1_enmienda_cesion` | ✅ mismo contrato | **cambia una parte** por cesión, pero cita el mismo contrato y fecha |

Los casos 4 a 9 son fáciles: cualquier chequeo razonable los resuelve. Los que
prueban el diseño son el 10 y el 11.

---

## Limitación conocida de este set

**Ningún par contiene la eliminación de una cláusula entera.** Los tres
documentos enmendados conservan todas las cláusulas del original; los cambios
son modificaciones y adiciones.

La única eliminación presente es *dentro* de una cláusula: en el par 1 cláusula
1 desaparece la expresión "e intransferible".

Esto importa porque el sistema debe distinguir **adiciones, eliminaciones y
modificaciones**. Con este set se puede demostrar la clasificación de adiciones
y modificaciones, y la de eliminación solo a nivel de texto interno, no de
cláusula completa.

---

## Cómo se usa

```
uv run python src/main.py \
  data/test_contracts/documento_1_original.jpg \
  data/test_contracts/documento_1_enmienda.jpg
```

La salida del pipeline (`ContractChangeOutput`) se compara contra la tabla del
par correspondiente. Los criterios de una corrida correcta:

1. `sections_changed` contiene exactamente las cláusulas marcadas como
   modificación o adición, y **ninguna** de las marcadas "sin cambios".
2. `summary_of_the_change` cita los valores concretos que cambiaron (12 → 24
   meses), no una generalización ("se actualizó el plazo").
3. Los tipos de cambio están bien clasificados: la cláusula 7 del par 1 y del
   par 2 es una **adición**, no una modificación.
