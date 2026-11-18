# Autenticacion por header x-api-key con hmac.compare_digest (API-06)
import hmac
from fastapi import Header, HTTPException, Request, status

from src.db.config import obtener_configuracion


def verificar_api_key(request: Request, x_api_key: str | None = Header(default=None, alias="x-api-key")):
    esperada = getattr(request.app.state, "api_key", None) or obtener_configuracion().api_key
    if not x_api_key or not hmac.compare_digest(str(x_api_key), str(esperada)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clave de API invalida o ausente (header x-api-key)",
        )
    return True
