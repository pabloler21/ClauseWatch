"""Paso 2 del pipeline: Agente de Contextualizacion (ContextualizationAgent).

Recibe los textos parseados de ambos documentos (original y enmienda) y
construye un mapa de correspondencia estructural entre secciones.
No extrae ni describe cambios: esa responsabilidad es exclusiva del Agente 2.
"""

import sys
from pathlib import Path

# Asegura que la raiz del proyecto este en sys.path al ejecutar como script suelto.
_project_root = str(Path(__file__).resolve().parents[2])
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
from src.prompts import load_prompt

# Carga variables de entorno para que LangChain resuelva las API keys necesarias.
load_dotenv()


# --- Prompt de Contextualizacion ---------------------------------------------
# Agente 1: Analista Legal Senior. Su regla negativa le prohibe extraer cambios,
# que es lo que lo separa del Agente 2 (rubrica 1.2).
CONTEXTUALIZATION_SYSTEM_PROMPT: str = load_prompt("contextualization_system_prompt")


def analyze_contract_structure(
    original_text: str,
    amendment_text: str,
    callbacks: list | None = None,
) -> str:
    """Analiza la estructura de dos documentos legales y genera un mapa de alineacion.

    Args:
        original_text: Texto del contrato original.
        amendment_text: Texto del contrato enmendado.
        callbacks: Lista opcional de callbacks (ej. Langfuse CallbackHandler).

    Returns:
        Un string con el mapa de alineacion estructural en formato Markdown.

    Raises:
        RuntimeError: Si el modelo corto la respuesta por limite de tokens.
    """
    # Modelo determinista con timeout y limite de tokens: valores en src/config.py.
    chat_model = init_chat_model(
        model=MODEL_NAME,
        temperature=MODEL_TEMPERATURE,
        timeout=MODEL_TIMEOUT_SECONDS,
        max_tokens=MODEL_MAX_TOKENS,
    )

    # Delimita claramente ambos documentos en el mensaje del usuario.
    user_prompt = (
        "Analyze the structure of the following two contracts and generate the structural alignment map.\n\n"
        f"--- ORIGINAL CONTRACT ---\n{original_text}\n\n"
        f"--- AMENDMENT / ADDENDUM ---\n{amendment_text}"
    )

    messages = [
        SystemMessage(content=CONTEXTUALIZATION_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    # invoke() es el metodo estandar de Runnables/ChatModels en LangChain.
    config = {"callbacks": callbacks} if callbacks else None
    response = chat_model.invoke(messages, config=config)

    # Previene truncamiento silencioso del mapa estructural.
    if response.response_metadata.get("finish_reason") == "length":
        raise RuntimeError(
            "El analisis de estructura quedo incompleto: se alcanzo el limite de tokens de salida. "
            "Aumentar MODEL_MAX_TOKENS en src/config.py y volver a ejecutar."
        )

    return response.text


if __name__ == "__main__":
    # sys.path ya quedo resuelto arriba, con el import de src.config.
    from src.image_parser import parse_contract_image

    project_root = Path(_project_root)
    sample_original = project_root / "data" / "test_contracts" / "documento_1_original.jpg"
    sample_amendment = project_root / "data" / "test_contracts" / "documento_1_enmienda.jpg"

    print("Parseando imagenes de prueba...")
    original_text = parse_contract_image(sample_original)
    amendment_text = parse_contract_image(sample_amendment)

    print("\nGenerando mapa contextual con ContextualizationAgent...\n")
    alignment_map = analyze_contract_structure(original_text, amendment_text)
    print(alignment_map)