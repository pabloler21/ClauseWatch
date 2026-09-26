"""Tests del registro de transcripciones (`src/parse_cache.py`).

No llaman a ningun modelo: trabajan sobre un directorio temporal y una imagen
real del set de prueba. Correr con:

    uv run python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Asegura que la raiz del proyecto este en sys.path para importar `src`.
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.parse_cache import (
    CacheEntryCorruptError,
    compute_cache_key,
    load_cached_transcription,
    save_transcription,
)

SAMPLE_IMAGE: Path = _project_root / "data" / "test_contracts" / "documento_1_original.jpg"
SAMPLE_TRANSCRIPTION: str = "CONTRATO DE LICENCIA\n1. Objeto: licencia no exclusiva."


class ParseCacheTest(unittest.TestCase):
    """Cada test usa un registro vacio propio, asi no dependen entre si."""

    def setUp(self) -> None:
        """Crea un directorio temporal que hace de registro."""
        self._temp_dir = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self._temp_dir.name)

    def tearDown(self) -> None:
        """Borra el directorio temporal."""
        self._temp_dir.cleanup()

    def test_empty_registry_is_a_miss(self) -> None:
        self.assertIsNone(load_cached_transcription(SAMPLE_IMAGE, self.cache_dir))

    def test_saved_transcription_is_a_hit(self) -> None:
        save_transcription(SAMPLE_IMAGE, SAMPLE_TRANSCRIPTION, self.cache_dir)
        cached = load_cached_transcription(SAMPLE_IMAGE, self.cache_dir)
        self.assertEqual(cached, SAMPLE_TRANSCRIPTION)

    def test_key_changes_with_model_or_prompt(self) -> None:
        base_key = compute_cache_key("abc", model_name="m1", prompt="p1")
        self.assertNotEqual(base_key, compute_cache_key("abc", model_name="m2", prompt="p1"))
        self.assertNotEqual(base_key, compute_cache_key("abc", model_name="m1", prompt="p2"))

    def test_corrupt_entry_raises(self) -> None:
        entry_path = save_transcription(SAMPLE_IMAGE, SAMPLE_TRANSCRIPTION, self.cache_dir)
        entry_path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(CacheEntryCorruptError):
            load_cached_transcription(SAMPLE_IMAGE, self.cache_dir)

    def test_missing_image_raises_like_the_parser(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_cached_transcription(self.cache_dir / "no_existe.jpg", self.cache_dir)


if __name__ == "__main__":
    unittest.main()
