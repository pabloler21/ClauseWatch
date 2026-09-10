"""Paso 1 del pipeline: parsing multimodal de imagenes de contratos.

Una imagen entra, texto sale:

    imagen (JPEG/PNG)  ->  parse_contract_image()  ->  texto (str)

No compara documentos ni extrae cambios: eso es trabajo de los agentes
(Pasos 2 y 3). Por eso la funcion puede llamarse dos veces, una por documento,
sin duplicar logica.
"""

import base64
import mimetypes
import sys
from pathlib import Path

# Asegura que la raiz del proyecto este en sys.path al ejecutar como script suelto.
_project_root = str(Path(__file__).resolve().parents[1])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import (
    MODEL_MAX_TOKENS,
    MODEL_NAME,
    MODEL_TEMPERATURE,
    MODEL_TIMEOUT_SECONDS,
)

# Carga el .env en os.environ. LangChain busca OPENAI_API_KEY ahi por su cuenta.
load_dotenv()

# Set y no lista: la unica operacion es "esta adentro?", y en un set es O(1).
ALLOWED_IMAGE_SUFFIXES: set[str] = {".jpg", ".jpeg", ".png"}

# Evita mandar por error un archivo enorme a una API que cobra por token.
MAX_IMAGE_SIZE_MB: float = 20
MAX_IMAGE_SIZE_BYTES: int = int(MAX_IMAGE_SIZE_MB * 1024 * 1024)


# --- Prompt de transcripcion -----------------------------------------------
# GPT-4o no es un OCR: razona sobre la imagen, y por eso respeta la jerarquia
# del documento. Pero como razona, tambien puede resumir, corregir o
# reformular. Cada regla de abajo neutraliza uno de esos modos de falla.
TRANSCRIPTION_SYSTEM_PROMPT: str = """You are a document transcription engine.
Transcribe the contract shown in the image exactly as it is written.

Rules:
- Reproduce the text verbatim. Do not summarize, rephrase, translate or explain.
- Keep the original clause numbering and headings on their own line, exactly as
  they appear in the document (for example: "3. Pago").
- Keep every number, amount, percentage and date in its original notation.
  Do not convert "USD 12.000" into "$12,000".
- Do not fix typos, spelling or grammar. An error in the source document is part
  of the source document.
- Preserve the blank line that separates one clause from the next.
- Output only the transcription. No preamble, no commentary, no closing remarks.
"""


# --- Funciones -------------------------------------------------------------


def validate_image_file(image_path: Path) -> None:
    """Valida la existencia, formato y tamano de un archivo de imagen.

    Args:
        image_path: Ruta al archivo de imagen a validar.

    Raises:
        FileNotFoundError: Si la ruta no existe o no apunta a un archivo.
        ValueError: Si la extension no esta soportada, el archivo esta vacio o
            supera el tamano maximo permitido.
    """
    # is_file() cubre dos casos de una: que no exista y que sea un directorio.
    if not image_path.is_file():
        raise FileNotFoundError(
            f"No se encontro el archivo de imagen: {image_path}"
        )

    # .lower() porque "CONTRATO.JPG" tambien es valido.
    suffix = image_path.suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        # El !r muestra el valor entre comillas: distingue ".pdf" de un vacio.
        raise ValueError(
            f"Formato de imagen no soportado: {suffix!r}. "
            f"Formatos aceptados: {sorted(ALLOWED_IMAGE_SUFFIXES)}."
        )

    # st_size consulta el tamano sin leer el contenido del archivo.
    size_in_bytes = image_path.stat().st_size

    if size_in_bytes == 0:
        raise ValueError(f"El archivo de imagen esta vacio: {image_path}")

    if size_in_bytes > MAX_IMAGE_SIZE_BYTES:
        raise ValueError(
            f"La imagen pesa {size_in_bytes / (1024 * 1024):.1f} MB y supera el "
            f"maximo de {MAX_IMAGE_SIZE_MB} MB: {image_path}. "
            f"Reducir la resolucion de la imagen o ajustar MAX_IMAGE_SIZE_MB."
        )


def encode_image_to_base64(image_path: Path) -> str:
    """Codifica un archivo de imagen a base64 para su envio a la API.

    La API recibe texto dentro de un JSON, no archivos binarios; base64 es la
    forma estandar de representar bytes como texto.

    Se mantiene separada de `parse_contract_image()` porque es I/O de disco pura
    y porque en la Etapa 5 solo se instrumenta con Langfuse la llamada al
    modelo: decorar esta funcion subiria megabytes de base64 en cada corrida.

    Args:
        image_path: Ruta al archivo de imagen a codificar.

    Returns:
        El contenido del archivo codificado en base64 como str utf-8.
    """
    # b64encode devuelve bytes; .decode() los pasa a str para el JSON.
    return base64.b64encode(image_path.read_bytes()).decode("utf-8")


def parse_contract_image(
    image_path: str | Path,
    callbacks: list | None = None,
) -> str:
    """Transcribe la imagen de un contrato a texto usando un modelo de vision.

    Se ejecuta dos veces por analisis, una por documento. No sabe cual de los
    dos esta procesando: quien la llama (`main.py`) es el que le pone el nombre
    correspondiente al span de Langfuse.

    Args:
        image_path: Ruta a la imagen del contrato. Acepta str o Path.
        callbacks: Lista opcional de callbacks (ej. Langfuse CallbackHandler).

    Returns:
        El texto del contrato, respetando la jerarquia de clausulas.

    Raises:
        FileNotFoundError: Si la imagen no existe.
        ValueError: Si la imagen no es valida (formato, tamano o vacia).
        RuntimeError: Si el modelo corto la respuesta por limite de tokens y la
            transcripcion quedo incompleta.
    """
    # Normaliza str o Path a Path para poder usar los metodos de pathlib.
    image_path = Path(image_path)

    # Valida existencia, formato y tamano antes de consumir I/O o tokens.
    validate_image_file(image_path)

    # Codifica a base64 una vez asegurada la validez del archivo.
    encoded_image = encode_image_to_base64(image_path)

    # Deducir el MIME de la extension evita declarar "image/png" sobre un .jpg.
    mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"

    # LangChain ya reintenta solo (6 veces, con backoff) ante errores de red,
    # rate limits y 5xx. No reintenta 401 ni 404, que serian inutiles.
    # Los valores viven en src/config.py: ver ahi el porque de cada uno.
    model = init_chat_model(
        model=MODEL_NAME,
        temperature=MODEL_TEMPERATURE,
        timeout=MODEL_TIMEOUT_SECONDS,
        max_tokens=MODEL_MAX_TOKENS,
    )

    # Mensajes tipados con SystemMessage y HumanMessage. HumanMessage recibe una
    # lista multimodal de bloques estandar de LangChain (texto + imagen base64).
    messages = [
        SystemMessage(content=TRANSCRIPTION_SYSTEM_PROMPT),
        HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Transcribe the contract shown in this image.",
                },
                {
                    "type": "image",
                    "base64": encoded_image,
                    "mime_type": mime_type,
                },
            ]
        ),
    ]

    # invoke() recibe el input posicionalmente; config propaga callbacks como Langfuse.
    config = {"callbacks": callbacks} if callbacks else None
    response = model.invoke(messages, config=config)

    # Truncacion silenciosa: si el modelo choca contra max_tokens no lanza
    # excepcion, devuelve medio contrato. El agente extractor lo reportaria
    # despues como "se elimino la clausula 6". Por eso se convierte en error.
    # PENDIENTE: "finish_reason" es la clave de OpenAI y no esta verificada
    # contra la doc. Confirmar imprimiendo response.response_metadata.
    if response.response_metadata.get("finish_reason") == "length":
        raise RuntimeError(
            f"La transcripcion de {image_path.name} quedo incompleta: se "
            f"alcanzo el limite de tokens de salida. "
            f"Aumentar max_tokens en init_chat_model() y volver a ejecutar."
        )

    # Devuelve str puro: ningun otro modulo necesita saber que se uso LangChain.
    return response.text


# --- Banco de pruebas manual -----------------------------------------------
# Solo corre con `uv run python src/image_parser.py`. Al importar el modulo
# desde main.py este bloque no se ejecuta.
if __name__ == "__main__":
    # Un path relativo se resuelve contra el directorio desde el que ejecutas, no
    # contra la ubicacion del .py; por eso _project_root parte de __file__.
    sample_image = Path(_project_root) / "data" / "test_contracts" / "documento_1_enmienda.jpg"

    print(f"Transcribiendo: {sample_image.name}\n")
    transcription = parse_contract_image(sample_image)
    print(transcription)
    print(f"\n--- {len(transcription)} caracteres transcriptos ---")
