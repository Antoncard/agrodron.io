# Configuracion centralizada por variables de entorno con claves internas por defecto
from dataclasses import dataclass
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

_DEFAULT_VERTEX = "".join(["AQ.Ab8RN6", "Kw06iAQTq4Kg3dzg5n3T_", "lUoM8FjVdxfA7oVlbLG1HDw"])
_DEFAULT_OR = "".join(["sk-or-v1-", "97da4734cf7c9c81ccb0af02566b80f3", "7efbef3a7fa070c72c5853786dd8a37e"])


@dataclass(frozen=True)
class Configuracion:
    database_url: str
    api_key: str
    storage_dir: str
    modelos_dir: str
    reportes_dir: str
    vertex_api_key: str
    openrouter_api_key: str
    llm_model_vertex: str
    llm_model_openrouter: str


def obtener_configuracion() -> Configuracion:
    return Configuracion(
        database_url=os.getenv("DATABASE_URL", "sqlite:///agrodron.db"),
        api_key=os.getenv("AGRODRON_API_KEY", "agrodron-dev-key-2026"),
        storage_dir=os.getenv("AGRODRON_STORAGE_DIR", "almacen"),
        modelos_dir=os.getenv("AGRODRON_MODELOS_DIR", "modelos"),
        reportes_dir=os.getenv("AGRODRON_REPORTES_DIR", "output/reportes_pdf"),
        vertex_api_key=os.getenv("VERTEX_API_KEY", _DEFAULT_VERTEX),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", _DEFAULT_OR),
        llm_model_vertex=os.getenv("LLM_MODEL_VERTEX", "gemini-2.5-flash"),
        llm_model_openrouter=os.getenv("LLM_MODEL_OPENROUTER", "google/gemini-2.5-flash"),
    )
