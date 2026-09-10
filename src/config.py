"""Configuracion centralizada de los modelos del pipeline.

Un unico lugar para los parametros de las tres llamadas a `init_chat_model()`.
Antes estos valores estaban repetidos literalmente en `image_parser.py`,
`contextualization_agent.py` y `extraction_agent.py`: cambiar de modelo obligaba
a tocar tres archivos y a acordarse de los tres.

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
# eso cada modulo verifica finish_reason == "length" despues de invocar.
MODEL_MAX_TOKENS: int = 4000
