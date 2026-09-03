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
from pydantic import ValidationError

from src.models import ContractChangeOutput

# Carga variables de entorno para resolver OPENAI_API_KEY.
load_dotenv()


# --- Prompt de Extraccion ----------------------------------------------------
# Agente 2: Auditor Legal Senior de Compliance.
# Su responsabilidad exclusiva es auditar y extraer cada cambio contractual.
# Especifica como poblar cada campo de ContractChangeOutput para guiar el
# structured output (segun lo acordado en CLAUDE.md §6).
EXTRACTION_SYSTEM_PROMPT: str = """You are a Senior Legal Compliance Auditor specializing in contractual change extraction.

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
"""


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
            modificadas, temas afectados y resumen detallado.

    Raises:
        RuntimeError: Si la respuesta no pudo validarse segun el esquema esperado.
    """
    # Modelo base configurado con timeouts y determinismo estricto.
    base_model = init_chat_model(
        model="openai:gpt-4o",
        temperature=0,
        timeout=60,
        max_tokens=4000,
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
    except ValidationError as error:
        raise RuntimeError(
            f"Fallo la validacion de ContractChangeOutput con Pydantic: {error}"
        ) from error

    if not isinstance(result, ContractChangeOutput):
        # Respaldo de seguridad: si el provider retornara dict, se valida explicitamente.
        return ContractChangeOutput.model_validate(result)

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