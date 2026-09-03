"""Entry point principal de ClauseWatch (Paso 5 del pipeline).

Orquesta el analisis multi-agente de contratos a partir de dos imagenes escaneadas:
1. Parsing multimodal con GPT-4o Vision (contrato original y adenda).
2. Mapeo estructural de correspondencias con ContextualizationAgent (Agente 1).
3. Extraccion y clasificacion de cambios legales con ExtractionAgent (Agente 2).
4. Validacion estructurada de salida con Pydantic (ContractChangeOutput).
5. Trazabilidad completa y observabilidad jerarquica instrumentada con Langfuse.

Uso por CLI:
    uv run python src/main.py <path_contrato_original> <path_enmienda>
"""

import argparse
import json
import sys
from pathlib import Path

# Asegura que la raiz del proyecto este en sys.path al invocar el script.
_project_root = str(Path(__file__).resolve().parents[1])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from dotenv import load_dotenv
from langfuse import get_client, observe
from langfuse.langchain import CallbackHandler

from src.agents.contextualization_agent import analyze_contract_structure
from src.agents.extraction_agent import extract_contract_changes
from src.image_parser import parse_contract_image
from src.models import ContractChangeOutput

# Carga variables de entorno (OPENAI_API_KEY, credenciales de Langfuse).
load_dotenv()


# --- Spans hijos instrumentados con Langfuse ---------------------------------
# Cada funcion representa una etapa del pipeline recomendada en la consigna.
# Al usar @observe(name=...), Langfuse las anida automaticamente bajo el span
# raiz activo, registrando inputs, outputs, latencia y errores.
# El CallbackHandler inyectado en cada llamada captura tokens, modelo y costo.


@observe(name="parse_original_contract")
def _step_parse_original(image_path: str | Path) -> str:
    """Span hijo: parsea la imagen del contrato original."""
    handler = CallbackHandler()
    return parse_contract_image(image_path, callbacks=[handler])


@observe(name="parse_amendment_contract")
def _step_parse_amendment(image_path: str | Path) -> str:
    """Span hijo: parsea la imagen de la enmienda o adenda."""
    handler = CallbackHandler()
    return parse_contract_image(image_path, callbacks=[handler])


@observe(name="contextualization_agent")
def _step_contextualization(original_text: str, amendment_text: str) -> str:
    """Span hijo: Agente 1 genera el mapa contextual de correspondencias."""
    handler = CallbackHandler()
    return analyze_contract_structure(
        original_text, amendment_text, callbacks=[handler]
    )


@observe(name="extraction_agent")
def _step_extraction(
    original_text: str,
    amendment_text: str,
    contextual_map: str,
) -> ContractChangeOutput:
    """Span hijo: Agente 2 audita y extrae los cambios validados con Pydantic."""
    handler = CallbackHandler()
    return extract_contract_changes(
        original_text, amendment_text, contextual_map, callbacks=[handler]
    )


# --- Span raiz de observabilidad ---------------------------------------------


@observe(name="contract-analysis")
def run_contract_analysis(
    original_path: str | Path,
    amendment_path: str | Path,
) -> ContractChangeOutput:
    """Ejecuta el pipeline completo bajo el span raiz 'contract-analysis'.

    Args:
        original_path: Ruta a la imagen del contrato original.
        amendment_path: Ruta a la imagen de la adenda/enmienda.

    Returns:
        ContractChangeOutput: Objeto Pydantic validado con los cambios detectados.
    """
    # 1. Parsing multimodal de ambos documentos
    print("[1/3] Parseando imagenes con GPT-4o Vision...")
    original_text = _step_parse_original(original_path)
    amendment_text = _step_parse_amendment(amendment_path)

    # 2. Contextualizacion estructural (Agente 1)
    print("[2/3] Generando mapa contextual con ContextualizationAgent...")
    contextual_map = _step_contextualization(original_text, amendment_text)

    # 3. Extraccion y estructuracion (Agente 2)
    print("[3/3] Extrayendo cambios con ExtractionAgent...")
    contract_changes = _step_extraction(
        original_text, amendment_text, contextual_map
    )

    return contract_changes


# --- Interfaz de linea de comandos (CLI) ------------------------------------


def parse_args() -> argparse.Namespace:
    """Configura y parsea los argumentos de linea de comandos."""
    parser = argparse.ArgumentParser(
        prog="clausewatch",
        description="ClauseWatch — Analisis y auditoria automatizada de contratos mediante agentes de IA.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "original_image",
        type=str,
        help="Ruta al archivo de imagen del contrato original (JPEG/PNG).",
    )
    parser.add_argument(
        "amendment_image",
        type=str,
        help="Ruta al archivo de imagen de la enmienda o adenda (JPEG/PNG).",
    )
    return parser.parse_args()


def main() -> int:
    """Entry point CLI del programa."""
    args = parse_args()

    # Inicializa el cliente de Langfuse para verificar conectividad y vaciar el buffer al final.
    lf_client = get_client()

    try:
        results = run_contract_analysis(args.original_image, args.amendment_image)
    except FileNotFoundError as e:
        print(f"\n[ERROR DE ARCHIVO] {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"\n[ERROR DE VALIDACION] {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"\n[ERROR DE EJECUCION] {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n[ERROR INESPERADO] {e}", file=sys.stderr)
        return 1
    finally:
        # Vacia el buffer de telemetria para garantizar que todos los spans lleguen a Langfuse Cloud.
        lf_client.flush()

    # Muestra el resultado estructurado final por salida estandar en formato JSON legible.
    print("\n" + "=" * 60)
    print("REPORTE FINAL DE CAMBIOS (ContractChangeOutput - Pydantic)")
    print("=" * 60)
    print(json.dumps(results.model_dump(), indent=2, ensure_ascii=False))

    # Imprime el link directo a la traza en Langfuse para auditoria y defensa oral.
    try:
        latest_trace = lf_client.api.trace.list(limit=1).data[0]
        trace_url = lf_client.get_trace_url(trace_id=latest_trace.id)
        print("\n" + "-" * 60)
        print(f"Trazabilidad Langfuse: {trace_url}")
        print("-" * 60)
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())