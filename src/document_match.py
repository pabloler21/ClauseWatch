"""Chequeo de correspondencia: verifica que los dos documentos sean el mismo contrato.

Corre entre el parsing y los agentes. Sin este chequeo, si se pasan el original
de un contrato y la enmienda de otro, el Agente 2 los compara igual y devuelve
cambios inventados dentro de un JSON valido.

No es un tercer agente: no analiza cambios, solo decide si tiene sentido
analizarlos. Por eso vive en src/ y no en src/agents/.

    texto original + texto enmienda  ->  check_document_match()  ->  DocumentMatchVerdict
"""

import sys
from pathlib import Path

# Asegura que la raiz del proyecto este en sys.path al ejecutar como script suelto.
_project_root = str(Path(__file__).resolve().parents[1])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from openai import LengthFinishReasonError
from pydantic import ValidationError

from src.config import (
    MATCH_CHECK_MAX_TOKENS,
    MATCH_CHECK_MODEL_NAME,
    MODEL_TEMPERATURE,
    MODEL_TIMEOUT_SECONDS,
)
from src.models import DocumentMatchVerdict
from src.prompts import load_prompt

# Carga variables de entorno para resolver OPENAI_API_KEY.
load_dotenv()


# --- Prompt de verificacion ---------------------------------------------------
# Las dos reglas centrales: cambiar una parte no hace otro contrato, y tener las
# mismas partes no hace el mismo contrato. Historial en docs/prompts/.
DOCUMENT_MATCH_SYSTEM_PROMPT: str = load_prompt("document_match_system_prompt")


def check_document_match(
    original_text: str,
    amendment_text: str,
    callbacks: list | None = None,
    model_name: str = MATCH_CHECK_MODEL_NAME,
) -> DocumentMatchVerdict:
    """Decide si el segundo documento corresponde al contrato del primero.

    Devuelve el veredicto y no decide que hacer con el: cortar el pipeline es
    responsabilidad del orquestador (`main.py`).

    Args:
        original_text: Texto transcripto del contrato original.
        amendment_text: Texto transcripto de la enmienda.
        callbacks: Lista opcional de callbacks (ej. Langfuse CallbackHandler).
        model_name: Identificador "proveedor:modelo". Por defecto el de
            `src/config.py`; se expone para comparar modelos en el banco de pruebas.

    Returns:
        DocumentMatchVerdict: El veredicto, con la evidencia citada y el motivo.

    Raises:
        RuntimeError: Si el modelo corto la respuesta por limite de tokens, o si
            la respuesta no pudo validarse segun `DocumentMatchVerdict`.
    """
    base_model = init_chat_model(
        model=model_name,
        temperature=MODEL_TEMPERATURE,
        timeout=MODEL_TIMEOUT_SECONDS,
        max_tokens=MATCH_CHECK_MAX_TOKENS,
    )
    structured_model = base_model.with_structured_output(DocumentMatchVerdict)

    user_prompt = (
        "Decide whether the second document belongs to the same agreement as the first one.\n\n"
        f"--- FIRST DOCUMENT (ORIGINAL CONTRACT) ---\n{original_text}\n\n"
        f"--- SECOND DOCUMENT (PRESENTED AS ITS AMENDMENT) ---\n{amendment_text}"
    )

    messages = [
        SystemMessage(content=DOCUMENT_MATCH_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    config = {"callbacks": callbacks} if callbacks else None
    try:
        result = structured_model.invoke(messages, config=config)

        # Respaldo por si el provider devolviera un dict en vez del modelo.
        if not isinstance(result, DocumentMatchVerdict):
            result = DocumentMatchVerdict.model_validate(result)
    except LengthFinishReasonError as error:
        raise RuntimeError(
            "El chequeo de correspondencia quedo incompleto: se alcanzo el limite "
            "de tokens de salida. Aumentar MATCH_CHECK_MAX_TOKENS en src/config.py."
        ) from error
    except ValidationError as error:
        raise RuntimeError(
            f"Fallo la validacion de DocumentMatchVerdict con Pydantic: {error}"
        ) from error

    return result


# --- Banco de pruebas: matriz de correspondencia ------------------------------
# Corre los 11 casos de data/test_contracts/README.md y compara contra el
# veredicto esperado. Uso: uv run python src/document_match.py [proveedor:modelo]
if __name__ == "__main__":
    from src.image_parser import parse_contract_image

    test_dir = Path(_project_root) / "data" / "test_contracts"

    # (original, segundo documento, veredicto esperado)
    expected_verdicts: list[tuple[str, str, bool]] = [
        ("documento_1_original", "documento_1_enmienda", True),
        ("documento_2_original", "documento_2_enmienda", True),
        ("documento_3_original", "documento_3_enmienda", True),
        ("documento_1_original", "documento_2_enmienda", False),
        ("documento_1_original", "documento_3_enmienda", False),
        ("documento_2_original", "documento_1_enmienda", False),
        ("documento_2_original", "documento_3_enmienda", False),
        ("documento_3_original", "documento_1_enmienda", False),
        ("documento_3_original", "documento_2_enmienda", False),
        ("documento_4_original", "documento_1_enmienda", False),
        ("documento_1_original", "documento_1_enmienda_cesion", True),
    ]

    selected_model = sys.argv[1] if len(sys.argv) > 1 else MATCH_CHECK_MODEL_NAME

    # Cada imagen se transcribe una sola vez: 8 llamadas de vision y no 22.
    image_names = sorted({name for case in expected_verdicts for name in case[:2]})
    print(f"Transcribiendo {len(image_names)} imagenes...")
    transcriptions = {
        name: parse_contract_image(test_dir / f"{name}.jpg") for name in image_names
    }

    print(f"\nChequeando {len(expected_verdicts)} casos con {selected_model}\n")
    hits = 0
    for case_number, (original, amendment, expected) in enumerate(expected_verdicts, 1):
        verdict = check_document_match(
            transcriptions[original], transcriptions[amendment], model_name=selected_model
        )
        is_hit = verdict.same_agreement == expected
        hits += is_hit
        print(
            f"{case_number:>2}. {'OK ' if is_hit else 'MAL'} "
            f"esperado={expected!s:<5} obtenido={verdict.same_agreement!s:<5} "
            f"{original} vs {amendment}\n    {verdict.reason}"
        )

    print(f"\nResultado: {hits}/{len(expected_verdicts)} con {selected_model}")
