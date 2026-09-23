"""Configuracion centralizada de los modelos del pipeline.

Un unico lugar para los parametros de las llamadas a `init_chat_model()`.
Antes estos valores estaban repetidos literalmente en `image_parser.py`,
`contextualization_agent.py` y `extraction_agent.py`: cambiar de modelo obligaba
a tocar tres archivos y a acordarse de los tres. El chequeo de correspondencia
(`document_match.py`) usa sus propias constantes, al final del archivo.

Las credenciales NO van aca. `OPENAI_API_KEY` y las claves de Langfuse salen del
`.env` y las resuelven LangChain y el SDK de Langfuse por su cuenta, porque son
secretos y este archivo se commitea.
"""

# Identificador "proveedor:modelo" que espera init_chat_model(). Cambiar el
# proveedor aca alcanza para todo el pipeline, si el paquete esta instalado.
MODEL_NAME: str = "openai:gpt-4o"

# Cero = lo mas determinista posible. Ni una transcripcion ni una auditoria legal
# quieren creatividad: ante la misma entrada, la misma salida.
MODEL_TEMPERATURE: float = 0

# Segundos antes de abortar una llamada. Un contrato tarda entre 5 y 20.
MODEL_TIMEOUT_SECONDS: int = 60

# Tope de tokens de salida por llamada. Protege el costo, pero puede truncar: por
# eso cada modulo convierte el truncamiento en un RuntimeError explicito.
MODEL_MAX_TOKENS: int = 4000


# --- Chequeo de correspondencia entre documentos -----------------------------
# Modelo propio porque la tarea es una clasificacion corta sobre texto, no
# vision ni auditoria. gpt-4o-mini acerto 11/11 en la matriz de prueba.
MATCH_CHECK_MODEL_NAME: str = "openai:gpt-4o-mini"

# El veredicto son cuatro campos cortos: 1000 tokens sobran y acotan el costo.
MATCH_CHECK_MAX_TOKENS: int = 1000
