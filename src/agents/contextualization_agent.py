"""Paso 2 del pipeline: Agente de Contextualizacion (ContextualizationAgent).

Recibe los textos parseados de ambos documentos (original y enmienda) y
construye un mapa de correspondencia estructural entre secciones.
No extrae ni describe cambios: esa responsabilidad es exclusiva del Agente 2.
"""

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

# Carga variables de entorno para que LangChain resuelva las API keys necesarias.
load_dotenv()


# --- Prompt de Contextualizacion ---------------------------------------------
# Agente 1: Analista Legal Senior.
# Su unico proposito es armar el mapa de alineacion estructural entre ambos
# documentos. La regla negativa prohibe explicitamente extraer cambios,
# preservando la separacion de responsabilidades evaluada en la rubrica 1.2.
CONTEXTUALIZATION_SYSTEM_PROMPT: str = """You are a Senior Legal Contract Analyst specializing in document structure mapping.

Your sole responsibility is to analyze the structure of two legal documents (an original contract and its amendment) and produce a comprehensive structural alignment map.

Instructions:
1. Identify all sections and clauses in both the original contract and the amendment.
2. Cross-reference sections between both documents:
   - Identify which clauses directly correspond to each other (even if numbered differently or rephrased).
   - Identify any new clauses introduced exclusively in the amendment.
   - Identify any clauses present in the original that are absent or omitted in the amendment.
3. For each mapped section, describe its general business and legal purpose in one concise sentence.
4. Output your analysis formatted clearly in Markdown using a comparative table followed by structural observations:
   - Section / Clause Identifier in Original Contract
   - Section / Clause Identifier in Amendment
   - Alignment Status (e.g., Corresponding, Added in Amendment, Omitted)
   - General Legal Purpose (in Spanish)

CRITICAL RULES:
- DO NOT extract, describe, or evaluate specific clause changes (for example, do NOT state "the price increased from X to Y" or "the term was extended").
- You are building a structural roadmap for an auditor, NOT performing the audit yourself.
- Write the section descriptions and structural notes in Spanish.
"""


def analyze_contract_structure(original_text: str, amendment_text: str) -> str:
    """Analiza la estructura de dos documentos legales y genera un mapa de alineacion.

    Args:
        original_text: Texto del contrato original.
        amendment_text: Texto del contrato enmendado.

    Returns:
        Un string con el mapa de alineacion estructural en formato Markdown.

    Raises:
        RuntimeError: Si el modelo corto la respuesta por limite de tokens.
    """
    # Modelo determinista con timeout y limite de tokens para control de costos.
    chat_model = init_chat_model(
        model="openai:gpt-4o",
        temperature=0,
        timeout=60,
        max_tokens=4000,
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
    response = chat_model.invoke(messages)

    # Previene truncamiento silencioso del mapa estructural.
    if response.response_metadata.get("finish_reason") == "length":
        raise RuntimeError(
            "El analisis de estructura quedo incompleto: se alcanzo el limite de tokens de salida. "
            "Aumentar max_tokens en init_chat_model() y volver a ejecutar."
        )

    return response.text


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Permite ejecutar este archivo directamente: `uv run python src/agents/contextualization_agent.py`
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from src.image_parser import parse_contract_image

    sample_original = project_root / "data" / "test_contracts" / "documento_1_original.jpg"
    sample_amendment = project_root / "data" / "test_contracts" / "documento_1_enmienda.jpg"

    print("Parseando imagenes de prueba...")
    original_text = parse_contract_image(sample_original)
    amendment_text = parse_contract_image(sample_amendment)

    print("\nGenerando mapa contextual con ContextualizationAgent...\n")
    alignment_map = analyze_contract_structure(original_text, amendment_text)
    print(alignment_map)