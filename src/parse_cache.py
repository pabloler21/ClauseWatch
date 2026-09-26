"""Registro local de transcripciones: evita parsear dos veces la misma imagen.

Comparar un contrato contra varias enmiendas pagaba el parsing del original en
cada corrida. Este modulo guarda cada transcripcion bajo una clave derivada del
contenido de la imagen, el modelo y el prompt:

    imagen  ->  compute_cache_key()  ->  data/parsed_contracts/<clave>.json

Es un cache por identidad exacta, no por similitud: una base vectorial exigiria
el texto (o sea, parsear) antes de poder buscar. No llama a ningun modelo ni
decide que hacer ante un fallo: esa politica es de `main.py`.
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Asegura que la raiz del proyecto este en sys.path al ejecutar como script suelto.
_project_root = str(Path(__file__).resolve().parents[1])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.config import MODEL_NAME, PARSE_CACHE_DIR
from src.image_parser import TRANSCRIPTION_SYSTEM_PROMPT, validate_image_file

# Extension de cada entrada del registro. JSON para poder abrirla y leerla a mano.
CACHE_ENTRY_SUFFIX: str = ".json"

# Campos obligatorios de una entrada. Si falta alguno, la entrada se considera corrupta.
REQUIRED_ENTRY_FIELDS: tuple[str, ...] = (
    "source_file",
    "image_sha256",
    "model_name",
    "prompt_sha256",
    "parsed_at",
    "transcription",
)


class CacheEntryCorruptError(Exception):
    """Una entrada del registro existe pero no se puede leer.

    Attributes:
        entry_path: Ruta del archivo corrupto, para poder mostrarla en el aviso.
    """

    def __init__(self, entry_path: Path, cause: str) -> None:
        """Guarda la ruta y arma el mensaje.

        Args:
            entry_path: Ruta del archivo de la entrada.
            cause: Descripcion corta de por que no se pudo leer.
        """
        super().__init__(f"Entrada del registro ilegible ({cause}): {entry_path}")
        self.entry_path = entry_path


def _sha256_hex(data: bytes) -> str:
    """Calcula el SHA-256 de unos bytes.

    Args:
        data: Contenido a hashear.

    Returns:
        El digest en hexadecimal (64 caracteres).
    """
    return hashlib.sha256(data).hexdigest()


def compute_cache_key(
    image_sha256: str,
    model_name: str = MODEL_NAME,
    prompt: str = TRANSCRIPTION_SYSTEM_PROMPT,
) -> str:
    """Deriva la clave de una transcripcion.

    Modelo y prompt forman parte de la clave porque cambiar cualquiera de los
    dos cambia el texto: sin ellos, editar el prompt devolveria texto viejo.

    Args:
        image_sha256: SHA-256 de los bytes de la imagen.
        model_name: Identificador del modelo de vision usado.
        prompt: System prompt de transcripcion usado.

    Returns:
        La clave en hexadecimal, usada como nombre del archivo de la entrada.
    """
    prompt_sha256 = _sha256_hex(prompt.encode("utf-8"))
    # El separador evita que dos combinaciones distintas concatenen al mismo string.
    combined = "|".join((image_sha256, model_name, prompt_sha256))
    return _sha256_hex(combined.encode("utf-8"))


def _entry_path(image_path: Path, cache_dir: Path) -> tuple[Path, str]:
    """Valida la imagen y calcula donde viviria su entrada.

    Args:
        image_path: Ruta a la imagen del contrato.
        cache_dir: Directorio del registro.

    Returns:
        La ruta del archivo de la entrada y el SHA-256 de la imagen.

    Raises:
        FileNotFoundError: Si la imagen no existe.
        ValueError: Si la imagen no es valida (formato, tamano o vacia).
    """
    # Misma validacion que el parsing: una imagen invalida falla igual con o sin cache.
    validate_image_file(image_path)
    image_sha256 = _sha256_hex(image_path.read_bytes())
    cache_key = compute_cache_key(image_sha256)
    return cache_dir / f"{cache_key}{CACHE_ENTRY_SUFFIX}", image_sha256


def load_cached_transcription(
    image_path: str | Path,
    cache_dir: Path = PARSE_CACHE_DIR,
) -> str | None:
    """Busca la transcripcion de una imagen en el registro.

    Args:
        image_path: Ruta a la imagen del contrato. Acepta str o Path.
        cache_dir: Directorio del registro. Parametro para poder testear.

    Returns:
        El texto transcripto, o None si la imagen no esta registrada con el
        modelo y prompt actuales.

    Raises:
        FileNotFoundError: Si la imagen no existe.
        ValueError: Si la imagen no es valida.
        CacheEntryCorruptError: Si la entrada existe pero no se puede leer.
    """
    entry_path, _ = _entry_path(Path(image_path), cache_dir)

    if not entry_path.is_file():
        return None

    try:
        entry = json.loads(entry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise CacheEntryCorruptError(entry_path, "JSON invalido") from error

    missing_fields = [field for field in REQUIRED_ENTRY_FIELDS if field not in entry]
    if missing_fields:
        raise CacheEntryCorruptError(entry_path, f"faltan campos {missing_fields}")

    return entry["transcription"]


def save_transcription(
    image_path: str | Path,
    transcription: str,
    cache_dir: Path = PARSE_CACHE_DIR,
) -> Path:
    """Guarda la transcripcion de una imagen en el registro.

    Args:
        image_path: Ruta a la imagen del contrato. Acepta str o Path.
        transcription: Texto devuelto por `parse_contract_image()`.
        cache_dir: Directorio del registro. Parametro para poder testear.

    Returns:
        La ruta del archivo de la entrada guardada.

    Raises:
        FileNotFoundError: Si la imagen no existe.
        ValueError: Si la imagen no es valida.
        OSError: Si no se pudo escribir en el directorio del registro.
    """
    image_path = Path(image_path)
    entry_path, image_sha256 = _entry_path(image_path, cache_dir)

    # La procedencia queda guardada: permite auditar de donde salio cada texto.
    entry = {
        "source_file": image_path.name,
        "image_sha256": image_sha256,
        "model_name": MODEL_NAME,
        "prompt_sha256": _sha256_hex(TRANSCRIPTION_SYSTEM_PROMPT.encode("utf-8")),
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "transcription": transcription,
    }

    cache_dir.mkdir(parents=True, exist_ok=True)

    # Escribe a un temporal y lo renombra: si el proceso muere a mitad de la
    # escritura, queda un .tmp huerfano y no una entrada a medio escribir.
    temp_path = entry_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(entry_path)

    return entry_path
