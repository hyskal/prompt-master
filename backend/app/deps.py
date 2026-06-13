import os
import secrets

from fastapi import Header, HTTPException


def exigir_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """Se a env API_KEY estiver definida, todo request precisa do header X-API-Key."""
    chave = os.environ.get("API_KEY")
    if not chave:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, chave):
        raise HTTPException(status_code=401, detail="Chave de API inválida ou ausente.")
