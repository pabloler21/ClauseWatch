"""Paso 3 del pipeline: Agente de Extraccion (ExtractionAgent).

Recibe los textos de ambos documentos (original y enmienda) junto con el mapa
contextual generado por ContextualizationAgent, y extrae con precision de auditor
cada cambio legal (modificaciones, adiciones y eliminaciones).
Produce una salida estructurada validada con el modelo Pydantic ContractChangeOutput.
"""

import sys
from pathlib import Path

# Asegura que la raiz del proyecto este en sys.path al ejecutar directamente como script.
_project_root = str(Path(__file__).resolve().parents[2])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from openai import LengthFinishReasonError
from pydantic import ValidationError

from src.config import (
    MODEL_MAX_TOKENS,
    MODEL_NAME,
    MODEL_TEMPERATURE,
    MODEL_TIMEOUT_SECONDS,
)
from src.models import ContractChangeOutput
from src.prompts import load_prompt

# Carga variables de entorno para resolver OPENAI_API_KEY.
load_dotenv()


# --- Prompt de Extraccion ----------------------------------------------------
# Agente 2: Auditor Legal Senior de Compliance. El porque de cada regla, con
# sus mediciones, esta en docs/prompts/extraction_system_prompt.md.
EXTRACTION_SYSTEM_PROMPT: str = load_prompt("extraction_system_prompt")


def extract_contract_changes(
    original_text: str,
    amendment_text: str,
    contextual_map: str,
    callbacks: list | None = None,
) -> ContractChangeOutput:
    """Extrae y estructura los cambios entre contratos usando el mapa de contextualizacion.

    Args:
        original_text: Texto completo transcripto del contrato original.
        amendment_text: Texto completo transcripto del contrato enmendado.
        contextual_map: Mapa de alineacion estructural generado por el Agente 1.
        callbacks: Lista opcional de callbacks (ej. Langfuse CallbackHandler).

    Returns:
        ContractChangeOutput: Objeto Pydantic validado con las secciones
            modificadas, los temas afectados, el resumen y la lista `changes`
            con cada cambio clasificado.

    Raises:
        RuntimeError: Si el modelo corto la respuesta por limite de tokens, o si
            la respuesta no pudo validarse segun `ContractChangeOutput`.
    """
    # Modelo base con timeouts y determinismo estricto: valores en src/config.py.
    base_model = init_chat_model(
        model=MODEL_NAME,
        temperature=MODEL_TEMPERATURE,
        timeout=MODEL_TIMEOUT_SECONDS,
        max_tokens=MODEL_MAX_TOKENS,
    )

    # with_structured_output vincula el JSON Schema de ContractChangeOutput a la API de OpenAI.
    structured_model = base_model.with_structured_output(ContractChangeOutput)

    # Delimita las tres fuentes de informacion que requiere el auditor.
    user_prompt = (
        "Compare the original contract and the amendment using the provided structural alignment map. "
        "Extract all changes and return the structured audit output.\n\n"
        f"--- STRUCTURAL ALIGNMENT MAP (AGENT 1) ---\n{contextual_map}\n\n"
        f"--- ORIGINAL CONTRACT ---\n{original_text}\n\n"
        f"--- AMENDMENT / ADDENDUM ---\n{amendment_text}"
    )

    messages = [
        SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    config = {"callbacks": callbacks} if callbacks else None
    try:
        result = structured_model.invoke(messages, config=config)

        # Respaldo por si el provider devolviera un dict: dentro del try para que
        # su ValidationError tenga el mismo tratamiento que el de invoke().
        if not isinstance(result, ContractChangeOutput):
            result = ContractChangeOutput.model_validate(result)
    except LengthFinishReasonError as error:
        # Con structured outputs el truncamiento no llega como finish_reason: el
        # SDK de OpenAI lo lanza como excepcion propia (verificado con max_tokens=30).
        raise RuntimeError(
            "La extraccion de cambios quedo incompleta: se alcanzo el limite de "
            "tokens de salida. Aumentar MODEL_MAX_TOKENS en src/config.py y volver "
            "a ejecutar."
        ) from error
    except ValidationError as error:
        raise RuntimeError(
            f"Fallo la validacion de ContractChangeOutput con Pydantic: {error}"
        ) from error

    return result


if __name__ == "__main__":
    import json

    from src.agents.contextualization_agent import analyze_contract_structure
    from src.image_parser import parse_contract_image

    project_root = Path(__file__).resolve().parents[2]
    sample_original = project_root / "data" / "test_contracts" / "documento_1_original.jpg"
    sample_amendment = project_root / "data" / "test_contracts" / "documento_1_enmienda.jpg"

    print("Parseando imagenes del Par 1...")
    orig_text = parse_contract_image(sample_original)
    amend_text = parse_contract_image(sample_amendment)

    print("\nGenerando mapa estructural (Agente 1)...")
    ctx_map = analyze_contract_structure(orig_text, amend_text)

    print("\nExtrayendo cambios estructurados (Agente 2)...")
    changes = extract_contract_changes(orig_text, amend_text, ctx_map)

    print(f"\nObjeto retornado: {type(changes).__name__}")
    print("\n--- JSON Validado con Pydantic ---")
    print(json.dumps(changes.model_dump(), indent=2, ensure_ascii=False))