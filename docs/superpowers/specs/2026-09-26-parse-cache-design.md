# Registro de transcripciones (caché del parsing) — diseño

Fecha: 2026-09-26. Opción elegida: **B** (caché ahora, base vectorial como fase 2).

## Problema

Comparar un mismo contrato original contra N enmiendas hoy paga N veces el
parsing de la misma imagen con GPT-4o Vision. En el par 1 cada parsing cuesta
~USD 0.006 y ~7-9 s (traza de referencia en `CLAUDE.md` §4).

## Por qué no una base vectorial para esto

Una base vectorial responde "¿qué se parece a esto?" sobre embeddings de texto.
Para consultarla habría que tener el texto, y para tener el texto hay que
parsear: se pagaría justo lo que se quiere ahorrar. Además la similitud es
aproximada, y una enmienda se parece mucho a su original: un acierto por
similitud podría devolver el texto equivocado sin error visible.

El problema es de **identidad exacta**, y eso se resuelve con un hash del
contenido del archivo.

## Diseño (fase 1)

**Clave.** `sha256(imagen) + MODEL_NAME + sha256(prompt de transcripción)`,
combinados en un único SHA-256. El modelo y el prompt entran en la clave porque
cambiar cualquiera de los dos cambia la transcripción: sin ellos, el caché
devolvería texto viejo después de editar el prompt.

**Almacenamiento.** Un archivo JSON por entrada en `data/parsed_contracts/`
(gitignoreado: son datos derivados y locales). Cada entrada guarda la
transcripción y su procedencia: nombre del archivo original, hash de la imagen,
modelo, hash del prompt y fecha. Esos registros son también la materia prima de
la fase 2.

Descartados: SQLite (más potente pero no se inspecciona abriendo un archivo, y
no hay consultas que lo justifiquen) y un único JSON con todas las entradas
(escrituras concurrentes y reescritura completa en cada guardado).

**Módulo.** `src/parse_cache.py`, sin llamadas a modelos. Expone
`load_cached_transcription()` y `save_transcription()`. No decide la política
ante fallos: eso lo hace el orquestador, igual que con `document_match.py`.

**Integración.** En `main.py`, un helper `_parse_with_cache()` que usan los dos
spans de parsing:

1. Si no hay `--refresh-cache`, busca en el registro. Acierto → devuelve el
   texto y marca el span con `metadata={"parse_cache": "hit"}`. No hay
   generación hija ni costo.
2. Fallo → `parse_contract_image()` como hoy, guarda y marca `"miss"` (o
   `"refresh"`).

**Errores.**
- Entrada corrupta (JSON inválido o campos faltantes) → `CacheEntryCorruptError`;
  el orquestador avisa por stderr, re-parsea y sobrescribe.
- Fallo al escribir (`OSError`) → aviso por stderr, el análisis sigue. Un caché
  roto no puede tumbar un análisis que ya se pagó.
- Imagen inválida → mismas excepciones que hoy (`validate_image_file()` corre
  antes de calcular el hash).
- Escritura a un archivo temporal + `Path.replace()`, para no dejar entradas a
  medio escribir si el proceso muere.

**CLI.** `--refresh-cache`: ignora lo guardado, parsea y sobrescribe.

**Tests.** `tests/test_parse_cache.py` con `unittest` (biblioteca estándar, sin
dependencias nuevas): miss con registro vacío, hit después de guardar, miss si
cambia el modelo o el prompt, entrada corrupta.

## Fuera de alcance — fase 2 (base vectorial)

Caso de uso: "llega una enmienda suelta, ¿a cuál contrato registrado
corresponde?". Sería leer los registros de `data/parsed_contracts/`, generar
embeddings del texto y buscar los candidatos más parecidos, confirmando con el
chequeo de correspondencia existente. Lleva su propia spec.

## Limitaciones

- Dos escaneos del mismo papel tienen bytes distintos → no hay acierto.
- Solo se cachea el parsing. El chequeo de correspondencia y los dos agentes
  corren siempre, porque dependen del par.
- Sin expiración ni límite de tamaño: con decenas de contratos no hace falta.
