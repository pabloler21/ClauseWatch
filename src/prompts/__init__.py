"""System prompts del pipeline, versionados como archivos de texto.

Cada prompt vive en `src/prompts/<nombre>.txt` y cada modulo carga el suyo con
`load_prompt()`. El contenido del archivo es exactamente lo que recibe el modelo:
la documentacion y el historial de versiones van en `docs/prompts/`.
"""

from pathlib import Path

# Se resuelve desde __file__ y no desde el directorio de trabajo, para que la
# carga funcione igual se ejecute el script desde donde se ejecute.
PROMPTS_DIR: Path = Path(__file__).resolve().parent

# .txt y no .md: el archivo es el texto que se envia, no un documento a renderizar.
PROMPT_FILE_SUFFIX: str = ".txt"


def load_prompt(prompt_name: str) -> str:
    """Lee un system prompt desde su archivo en `src/prompts/`.

    Args:
        prompt_name: Nombre del archivo sin extension
            (por ejemplo, "extraction_system_prompt").

    Returns:
        El texto completo del prompt, tal como se le envia al modelo.

    Raises:
        FileNotFoundError: Si no existe un archivo con ese nombre.
        ValueError: Si el archivo existe pero esta vacio.
    """
    prompt_path = PROMPTS_DIR / f"{prompt_name}{PROMPT_FILE_SUFFIX}"

    if not prompt_path.is_file():
        raise FileNotFoundError(
            f"No se encontro el prompt {prompt_name!r} en {PROMPTS_DIR}."
        )

    # utf-8 explicito: en Windows el default es cp1252 y romperia los acentos.
    prompt_text = prompt_path.read_text(encoding="utf-8")

    # Un prompt vacio no falla en la API: el modelo responde igual, sin reglas.
    if not prompt_text.strip():
        raise ValueError(f"El archivo del prompt {prompt_name!r} esta vacio.")

    return prompt_text
