"""Prompt Master — API FastAPI que alimenta o portal estático em HTMX."""

import inspect
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from .api_routes import router as api_router
from .db import init_db
from .deps import exigir_api_key
from .ui_routes import router as ui_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Prompt Master API", version="1.0.0", lifespan=lifespan)

app.include_router(api_router, prefix="/api", dependencies=[Depends(exigir_api_key)])
app.include_router(ui_router, prefix="/ui", dependencies=[Depends(exigir_api_key)])

# CORS: o frontend roda em outra origem (GitHub Pages). Sem allow_credentials —
# X-API-Key é header comum e credenciais são inválidas com origem "*".
# allow_private_network: o Chrome (Private Network Access) exige aprovação no
# preflight quando uma página pública chama uma API em localhost/rede local.
origens = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
_cors_kwargs = dict(
    allow_origins=origens,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
_cors_nativo_pna = (
    "allow_private_network" in inspect.signature(CORSMiddleware.__init__).parameters
)
if _cors_nativo_pna:
    _cors_kwargs["allow_private_network"] = True
app.add_middleware(CORSMiddleware, **_cors_kwargs)

if not _cors_nativo_pna:

    class PrivateNetworkMiddleware(BaseHTTPMiddleware):
        """Fallback para Starlette antigo, sem allow_private_network: anexa o
        header de aprovação ao preflight. Registrado DEPOIS do CORS para ficar
        mais externo e alterar a resposta que o CORSMiddleware curto-circuita."""

        async def dispatch(self, request, call_next):
            response = await call_next(request)
            if (
                request.method == "OPTIONS"
                and request.headers.get("access-control-request-private-network") == "true"
            ):
                response.headers["Access-Control-Allow-Private-Network"] = "true"
            return response

    app.add_middleware(PrivateNetworkMiddleware)

# Serve o frontend (docs/) na raiz quando disponível: prático para uso local e
# para a imagem Docker autossuficiente. As rotas /api, /ui e /docs (Swagger)
# têm precedência sobre o mount.
_candidatos_docs = [
    os.environ.get("DOCS_DIR"),
    str(Path(__file__).resolve().parents[2] / "docs"),  # checkout do repositório
    str(Path(__file__).resolve().parents[1] / "docs"),  # imagem Docker (/app/docs)
]
DOCS_DIR = next((c for c in _candidatos_docs if c and Path(c).is_dir()), None)

if DOCS_DIR:
    app.mount("/", StaticFiles(directory=DOCS_DIR, html=True), name="frontend")
else:

    @app.get("/")
    def raiz():
        # Sem auth: serve de health check para plataformas de deploy.
        return {"app": "prompt-master", "status": "ok"}
