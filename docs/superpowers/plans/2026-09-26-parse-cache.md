# Plan — registro de transcripciones

Spec: `docs/superpowers/specs/2026-09-26-parse-cache-design.md`.
Un commit por tarea.

1. **`feat`: módulo `src/parse_cache.py`.** Constante `PARSE_CACHE_DIR` en
   `src/config.py`, `data/parsed_contracts/` en `.gitignore`. Funciones de hash,
   clave, lectura y escritura atómica, `CacheEntryCorruptError`.
2. **`test`: `tests/test_parse_cache.py`.** `unittest` sobre un directorio
   temporal. Verificar: `uv run python -m unittest discover -s tests -v`.
3. **`feat`: integración en `main.py`.** `_parse_with_cache()`, flag
   `--refresh-cache`, metadata `parse_cache` en los spans de parsing. Verificar:
   par 1 dos veces; la segunda debe decir "desde el registro" y no generar
   llamadas a GPT-4o en el parsing.
4. **`docs`: README.** Uso del flag, decisión técnica y limitaciones.
5. **`docs`: `CLAUDE.md`.** Estado del repo y la decisión tomada.
