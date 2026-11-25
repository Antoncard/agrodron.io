# Configuracion centralizada por variables de entorno (BD-N5: sin credenciales en el repositorio)
from dataclasses import dataclass
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


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
    cors_origins: tuple[str, ...] = ("*",)


def _parsear_origenes_cors(raw: str) -> tuple[str, ...]:
    items = [x.strip() for x in (raw or "").split(",") if x.strip()]
    return tuple(items) if items else ("*",)


def obtener_configuracion() -> Configuracion:
    return Configuracion(
        database_url=os.getenv("DATABASE_URL", "sqlite:///agrodron.db"),
        api_key=os.getenv("AGRODRON_API_KEY", "agrodron-dev-key-2026"),
        storage_dir=os.getenv("AGRODRON_STORAGE_DIR", "almacen"),
        modelos_dir=os.getenv("AGRODRON_MODELOS_DIR", "modelos"),
        reportes_dir=os.getenv("AGRODRON_REPORTES_DIR", "output/reportes_pdf"),
        vertex_api_key=os.getenv("VERTEX_API_KEY", ""),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        llm_model_vertex=os.getenv("LLM_MODEL_VERTEX", "gemini-2.5-flash"),
        llm_model_openrouter=os.getenv("LLM_MODEL_OPENROUTER", "google/gemini-2.5-flash"),
        cors_origins=_parsear_origenes_cors(os.getenv("AGRODRON_CORS_ORIGINS", "*")),
    )
