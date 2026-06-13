"""Rotas de fragmentos HTML (/ui), consumidas pelo HTMX do portal.

Toda mutação re-renderiza a lista inteira (lista.html) dentro de #lista — assim
chips, contagens, seção de fixados e anexos ficam sempre consistentes.
"""

from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from . import db
from .arquivos import ACCEPT_HTML, MAX_ARQUIVOS_POR_PROMPT, anexar_uploads, processar_import
from .db import get_db
from .schemas import PromptIn

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _data_br(valor: str) -> str:
    try:
        return datetime.fromisoformat(valor).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return str(valor)


def _tamanho_legivel(n) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


templates.env.filters["data_br"] = _data_br
templates.env.filters["tamanho_legivel"] = _tamanho_legivel


def _render_lista(request: Request, conn, categoria: str | None = None, q: str | None = None):
    prompts = db.listar_prompts(conn, categoria, q)
    fixados = [p for p in prompts if p["fixado"]]
    grupos: dict[str, list[dict]] = {}
    for p in prompts:
        if not p["fixado"]:
            grupos.setdefault(p["categoria"], []).append(p)
    grupos = dict(sorted(grupos.items(), key=lambda kv: kv[0].casefold()))
    categorias = db.contar_por_categoria(conn)
    return templates.TemplateResponse(
        request,
        "lista.html",
        {
            "fixados": fixados,
            "grupos": grupos,
            "categorias": categorias,
            "total": sum(qtd for _, qtd in categorias),
            "filtro": categoria or "",
            "qs_filtro": f"?categoria={quote(categoria)}" if categoria else "",
            "max_arquivos": MAX_ARQUIVOS_POR_PROMPT,
            "accept": ACCEPT_HTML,
        },
    )


@router.get("/prompts")
def ui_listar(request: Request, categoria: str | None = None, q: str | None = None, conn=Depends(get_db)):
    return _render_lista(request, conn, categoria or None, q or None)


@router.post("/prompts")
def ui_criar(
    request: Request,
    titulo: str = Form(""),
    prompt: str = Form(""),
    categoria: str = Form("Geral"),
    tags: str = Form(""),
    arquivos: list[UploadFile] | None = File(None),
    conn=Depends(get_db),
):
    lista_tags = [t.strip() for t in tags.split(",") if t.strip()][:3]
    try:
        dados = PromptIn(titulo=titulo, prompt=prompt, categoria=categoria, tags=lista_tags)
    except ValidationError:
        raise HTTPException(400, "Preencha o título e o texto do prompt.")
    criado = db.inserir_prompt(
        conn, dados.titulo, dados.prompt, dados.categoria, dados.tags, db.agora_iso()
    )
    anexar_uploads(conn, criado["id"], arquivos or [])
    conn.commit()
    return _render_lista(request, conn)


@router.post("/prompts/import")
def ui_importar(
    request: Request,
    arquivo: UploadFile = File(...),
    modo: str = Form("mesclar"),
    conn=Depends(get_db),
):
    processar_import(conn, arquivo, modo)
    return _render_lista(request, conn)


@router.post("/prompts/{prompt_id}/duplicar")
def ui_duplicar(
    request: Request,
    prompt_id: int,
    categoria: str | None = None,
    conn=Depends(get_db),
):
    if not db.duplicar_prompt(conn, prompt_id):
        raise HTTPException(404, "Prompt não encontrado.")
    conn.commit()
    return _render_lista(request, conn, categoria or None)


@router.get("/prompts/{prompt_id}/editar")
def ui_form_editar(
    request: Request,
    prompt_id: int,
    categoria: str | None = None,
    conn=Depends(get_db),
):
    p = db.obter_prompt(conn, prompt_id)
    if not p:
        raise HTTPException(404, "Prompt não encontrado.")
    qs_filtro = f"?categoria={quote(categoria)}" if categoria else ""
    return templates.TemplateResponse(
        request, "form-editar.html", {"p": p, "qs_filtro": qs_filtro}
    )


@router.post("/prompts/{prompt_id}/editar")
def ui_salvar_edicao(
    request: Request,
    prompt_id: int,
    titulo: str = Form(""),
    prompt: str = Form(""),
    categoria: str = Form("Geral"),
    tags: str = Form(""),
    conn=Depends(get_db),
):
    lista_tags = [t.strip() for t in tags.split(",") if t.strip()][:3]
    try:
        dados = PromptIn(titulo=titulo, prompt=prompt, categoria=categoria, tags=lista_tags)
    except ValidationError:
        raise HTTPException(400, "Preencha o título e o texto do prompt.")
    p = db.atualizar_prompt(conn, prompt_id, dados.titulo, dados.prompt, dados.categoria, dados.tags)
    if not p:
        raise HTTPException(404, "Prompt não encontrado.")
    conn.commit()
    return _render_lista(request, conn)


@router.delete("/prompts/{prompt_id}")
def ui_excluir(
    request: Request,
    prompt_id: int,
    categoria: str | None = None,
    conn=Depends(get_db),
):
    if not db.excluir_prompt(conn, prompt_id):
        raise HTTPException(404, "Prompt não encontrado.")
    conn.commit()
    return _render_lista(request, conn, categoria or None)


@router.patch("/prompts/{prompt_id}/fixar")
def ui_fixar(
    request: Request,
    prompt_id: int,
    categoria: str | None = None,
    conn=Depends(get_db),
):
    if not db.alternar_fixado(conn, prompt_id):
        raise HTTPException(404, "Prompt não encontrado.")
    conn.commit()
    return _render_lista(request, conn, categoria or None)


@router.post("/prompts/{prompt_id}/arquivos")
def ui_anexar(
    request: Request,
    prompt_id: int,
    categoria: str | None = None,
    arquivos: list[UploadFile] | None = File(None),
    conn=Depends(get_db),
):
    if not db.obter_prompt(conn, prompt_id):
        raise HTTPException(404, "Prompt não encontrado.")
    if not anexar_uploads(conn, prompt_id, arquivos or []):
        raise HTTPException(400, "Selecione ao menos um arquivo.")
    conn.commit()
    return _render_lista(request, conn, categoria or None)


@router.delete("/prompts/{prompt_id}/arquivos/{arquivo_id}")
def ui_excluir_arquivo(
    request: Request,
    prompt_id: int,
    arquivo_id: int,
    categoria: str | None = None,
    conn=Depends(get_db),
):
    if not db.excluir_arquivo(conn, prompt_id, arquivo_id):
        raise HTTPException(404, "Arquivo não encontrado.")
    conn.commit()
    return _render_lista(request, conn, categoria or None)
