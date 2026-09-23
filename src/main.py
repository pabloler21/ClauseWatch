"""Entry point principal de ClauseWatch (Paso 5 del pipeline).

Orquesta el analisis multi-agente de contratos a partir de dos imagenes escaneadas:
1. Parsing multimodal con GPT-4o Vision (contrato original y adenda).
   Chequeo de correspondencia: corta si los documentos no son el mismo contrato.
2. Mapeo estructural de correspondencias con ContextualizationAgent (Agente 1).
3. Extraccion y clasificacion de cambios legales con ExtractionAgent (Agente 2).
4. Validacion estructurada de salida con Pydantic (ContractChangeOutput).
5. Trazabilidad completa y observabilidad jerarquica instrumentada con Langfuse.

Uso por CLI:
    uv run python src/main.py <path_contrato_original> <path_enmienda> [--skip-match-check]
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
from langfuse import Langfuse, get_client, observe
from langfuse.langchain import CallbackHandler

from src.agents.contextualization_agent import analyze_contract_structure
from src.agents.extraction_agent import extract_contract_changes
from src.document_match import check_document_match
from src.image_parser import parse_contract_image
from src.models import ContractChangeOutput, DocumentMatchVerdict

# Carga variables de entorno (OPENAI_API_KEY, credenciales de Langfuse).
load_dotenv()

# Codigos de salida de la CLI. El 2 lo reserva argparse para argumentos invalidos.
EXIT_SUCCESS: int = 0
EXIT_FAILURE: int = 1
# Propio y no 1: un script que llame a la CLI distingue "rechazado" de "fallo".
EXIT_DOCUMENTS_MISMATCH: int = 3


class DocumentMismatchError(Exception):
    """Los dos documentos no pertenecen al mismo contrato y no se comparan.

    Hereda de Exception y no de ValueError: si no, `main()` la mostraria como
    un error de validacion de la imagen.

    Attributes:
        reason: Motivo del rechazo en espanol, tal como lo dio el chequeo.
    """

    def __init__(self, reason: str) -> None:
        """Guarda el motivo del rechazo.

        Args:
            reason: Motivo del rechazo en espanol.
        """
        super().__init__(reason)
        self.reason = reason


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


@observe(name="document_match_check")
def _step_document_match(
    original_text: str,
    amendment_text: str,
) -> DocumentMatchVerdict | None:
    """Span hijo: verifica que ambos documentos sean el mismo contrato.

    Si el chequeo mismo falla (red, timeout, validacion), el analisis sigue:
    es un control de apoyo, no un requisito. El fallo queda marcado en el span.

    Args:
        original_text: Texto transcripto del contrato original.
        amendment_text: Texto transcripto de la enmienda.

    Returns:
        El veredicto, o None si el chequeo no pudo completarse.
    """
    handler = CallbackHandler()
    try:
        return check_document_match(original_text, amendment_text, callbacks=[handler])
    except Exception as error:
        print(
            f"\n[AVISO] No se pudo verificar la correspondencia ({type(error).__name__}). "
            f"El analisis continua sin ese control.",
            file=sys.stderr,
        )
        get_client().update_current_span(
            level="WARNING",
            status_message=f"Chequeo de correspondencia omitido: {type(error).__name__}",
        )
        return None


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
    skip_match_check: bool = False,
) -> ContractChangeOutput:
    """Ejecuta el pipeline completo bajo el span raiz 'contract-analysis'.

    El trace id de Langfuse lo administra `main()` y se inyecta con el kwarg
    `langfuse_trace_id`, que @observe consume y nunca llega hasta aca: el
    pipeline no sabe nada de observabilidad y devuelve solo su resultado.

    Args:
        original_path: Ruta a la imagen del contrato original.
        amendment_path: Ruta a la imagen de la adenda/enmienda.
        skip_match_check: Si es True, no verifica que ambos documentos sean el
            mismo contrato. Queda registrado en la metadata del span raiz.

    Returns:
        El objeto Pydantic validado con los cambios detectados entre ambos
        documentos.

    Raises:
        DocumentMismatchError: Si el chequeo determina que los documentos no
            pertenecen al mismo contrato. Se lanza antes de correr los agentes.
    """
    # El progreso va a stderr para que stdout quede con el JSON puro y se pueda redirigir.
    # 1. Parsing multimodal de ambos documentos
    print("[1/4] Parseando imagenes con GPT-4o Vision...", file=sys.stderr)
    original_text = _step_parse_original(original_path)
    amendment_text = _step_parse_amendment(amendment_path)

    # 2. Chequeo de correspondencia: despues del parsing porque decide con el
    # texto de GPT-4o, y antes de los agentes porque son ~57 % del costo.
    if skip_match_check:
        print("[2/4] Chequeo de correspondencia omitido por --skip-match-check.", file=sys.stderr)
        get_client().update_current_span(metadata={"match_check": "skipped_by_user"})
    else:
        print("[2/4] Verificando que ambos documentos sean el mismo contrato...", file=sys.stderr)
        verdict = _step_document_match(original_text, amendment_text)
        if verdict is not None and not verdict.same_agreement:
            raise DocumentMismatchError(verdict.reason)

    # 3. Contextualizacion estructural (Agente 1)
    print("[3/4] Generando mapa contextual con ContextualizationAgent...", file=sys.stderr)
    contextual_map = _step_contextualization(original_text, amendment_text)

    # 4. Extraccion y estructuracion (Agente 2)
    print("[4/4] Extrayendo cambios con ExtractionAgent...", file=sys.stderr)
    contract_changes = _step_extraction(
        original_text, amendment_text, contextual_map
    )

    return contract_changes


# --- Interfaz de linea de comandos (CLI) ------------------------------------


def parse_args() -> argparse.Namespace:
    """Configura y parsea los argumentos de linea de comandos.

    Returns:
        Los argumentos parseados: `original_image`, `amendment_image` y
        `skip_match_check`.
    """
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
    parser.add_argument(
        "--skip-match-check",
        action="store_true",
        help=(
            "No verificar que ambos documentos sean el mismo contrato. Para cuando "
            "el chequeo rechaza un par que el usuario sabe que es valido."
        ),
    )
    return parser.parse_args()


def _resolve_trace_url(client: Langfuse, trace_id: str) -> str | None:
    """Construye la URL de una traza sin dejar que un fallo tumbe el reporte.

    `get_trace_url()` consulta la API de Langfuse para resolver el project id,
    asi que puede fallar por red o por credenciales ausentes. Un problema de
    telemetria no puede invalidar un analisis que ya se ejecuto y se pago.

    Args:
        client: Cliente de Langfuse ya inicializado.
        trace_id: Identificador de la traza cuya URL se quiere construir.

    Returns:
        La URL de la traza en la UI de Langfuse, o None si no se pudo resolver.
    """
    try:
        return client.get_trace_url(trace_id=trace_id)
    except Exception as e:
        # El str() de un error HTTP incluye todos los headers de la respuesta:
        # ruido inutil en una CLI. Alcanza el tipo y la causa mas probable.
        print(
            f"\n[AVISO] No se pudo resolver la URL de la traza ({type(e).__name__}). "
            f"Revisar las credenciales de Langfuse en el .env. "
            f"El analisis no se vio afectado.",
            file=sys.stderr,
        )
        return None


def main() -> int:
    """Entry point CLI del programa.

    Returns:
        El codigo de salida: EXIT_SUCCESS, EXIT_FAILURE o EXIT_DOCUMENTS_MISMATCH.
    """
    # Sin esto, al redirigir la salida en Windows Python usa la codepage de la
    # consola (cp1252) y el JSON con acentos deja de ser UTF-8 valido.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    args = parse_args()

    # Inicializa el cliente de Langfuse para verificar conectividad y vaciar el buffer al final.
    lf_client = get_client()

    # El trace id se genera aca y se le presta al pipeline. Resolver la URL es
    # responsabilidad del orquestador, no del analisis.
    trace_id = lf_client.create_trace_id()

    # Un unico punto de salida: los except marcan el codigo pero no cortan, asi
    # el link de la traza se imprime tambien cuando el pipeline falla.
    exit_code = EXIT_SUCCESS
    results: ContractChangeOutput | None = None

    try:
        results = run_contract_analysis(
            args.original_image,
            args.amendment_image,
            skip_match_check=args.skip_match_check,
            langfuse_trace_id=trace_id,
        )
    except DocumentMismatchError as e:
        print(
            f"\n[DOCUMENTOS NO CORRESPONDEN] Los contratos son distintos y no se "
            f"pueden comparar.\nMotivo: {e.reason}\n"
            f"Si el par es correcto, volver a ejecutar con --skip-match-check.",
            file=sys.stderr,
        )
        exit_code = EXIT_DOCUMENTS_MISMATCH
    except FileNotFoundError as e:
        print(f"\n[ERROR DE ARCHIVO] {e}", file=sys.stderr)
        exit_code = EXIT_FAILURE
    except ValueError as e:
        print(f"\n[ERROR DE VALIDACION] {e}", file=sys.stderr)
        exit_code = EXIT_FAILURE
    except RuntimeError as e:
        print(f"\n[ERROR DE EJECUCION] {e}", file=sys.stderr)
        exit_code = EXIT_FAILURE
    except Exception as e:
        print(f"\n[ERROR INESPERADO] {e}", file=sys.stderr)
        exit_code = EXIT_FAILURE
    finally:
        # Vacia el buffer de telemetria para garantizar que todos los spans lleguen a Langfuse Cloud.
        lf_client.flush()

    # Con el trace id explicito la URL no depende del span activo, que ya cerro.
    trace_url = _resolve_trace_url(lf_client, trace_id)

    # Los encabezados son decoracion y van a stderr; el JSON es el resultado y va a stdout.
    if results is not None:
        print("\n" + "=" * 60, file=sys.stderr)
        print("REPORTE FINAL DE CAMBIOS (ContractChangeOutput - Pydantic)", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(json.dumps(results.model_dump(), indent=2, ensure_ascii=False))

    # El link se imprime en las dos salidas: si el pipeline fallo, la traza es
    # justamente donde se ve en que etapa fallo.
    if trace_url:
        print("\n" + "-" * 60, file=sys.stderr)
        print(f"Trazabilidad Langfuse: {trace_url}", file=sys.stderr)
        print("-" * 60, file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())