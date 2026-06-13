"""Rotas JSON (/api): a API REST consumida programaticamente e pelo JS do portal."""

import json
import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from . import db
from .arquivos import anexar_uploads, processar_import
from .db import get_db
from .schemas import ArquivoOut, PromptIn, PromptOut, PromptUpdate

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "app": "prompt-master"}


@router.get("/prompts", response_model=list[PromptOut])
def listar(categoria: str | None = None, conn=Depends(get_db)):
    return db.listar_prompts(conn, categoria)


@router.post("/prompts", response_model=PromptOut, status_code=201)
def criar(dados: PromptIn, conn=Depends(get_db)):
    criado = db.inserir_prompt(
        conn, dados.titulo, dados.prompt, dados.categoria, dados.tags, db.agora_iso()
    )
    conn.commit()
    return criado


# Declaradas antes de /prompts/{id}: "export"/"import" não podem cair no path int.
@router.get("/prompts/export")
def exportar(conn=Depends(get_db)):
    prompts = db.listar_prompts(conn)
    for p in prompts:
        p["arquivos"] = db.listar_arquivos_completos(conn, p["id"])
    corpo = {
        "versao": 1,
        "exportado_em": db.agora_iso(),
        "total": len(prompts),
        "prompts": prompts,
    }
    return Response(
        content=json.dumps(corpo, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="prompts-export.json"'},
    )


@router.post("/prompts/import")
def importar(
    arquivo: UploadFile = File(...),
    modo: str = Form("mesclar"),
    conn=Depends(get_db),
):
    return processar_import(conn, arquivo, modo)


@router.get("/prompts/{prompt_id}/export")
def exportar_um(prompt_id: int, conn=Depends(get_db)):
    p = db.obter_prompt(conn, prompt_id)
    if not p:
        raise HTTPException(404, "Prompt não encontrado.")
    p["arquivos"] = db.listar_arquivos_completos(conn, prompt_id)
    instrucao = (
        "Você recebeu um prompt exportado do Prompt Master. "
        "Execute o campo 'prompt' como instrução principal. "
        "Se houver itens em 'arquivos', o campo 'conteudo' de cada um é contexto adicional para a tarefa. "
        "Ignore campos técnicos como 'versao', 'exportado_em', 'id', 'data', 'fixado'."
    )
    corpo = {
        "_instrucao": instrucao,
        "versao": 1,
        "exportado_em": db.agora_iso(),
        "total": 1,
        "prompts": [p],
    }
    nome_base = re.sub(r"[^A-Za-z0-9._-]", "_", p["titulo"])[:50] or f"prompt-{prompt_id}"
    return Response(
        content=json.dumps(corpo, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{nome_base}.json"'},
    )


@router.get("/prompts/{prompt_id}", response_model=PromptOut)
def obter(prompt_id: int, conn=Depends(get_db)):
    p = db.obter_prompt(conn, prompt_id)
    if not p:
        raise HTTPException(404, "Prompt não encontrado.")
    return p


@router.delete("/prompts/{prompt_id}", status_code=204)
def excluir(prompt_id: int, conn=Depends(get_db)):
    if not db.excluir_prompt(conn, prompt_id):
        raise HTTPException(404, "Prompt não encontrado.")
    conn.commit()


@router.patch("/prompts/{prompt_id}", response_model=PromptOut)
def atualizar(prompt_id: int, dados: PromptUpdate, conn=Depends(get_db)):
    p = db.atualizar_prompt(
        conn, prompt_id, dados.titulo, dados.prompt, dados.categoria, dados.tags
    )
    if not p:
        raise HTTPException(404, "Prompt não encontrado.")
    conn.commit()
    return p


@router.patch("/prompts/{prompt_id}/fixar", response_model=PromptOut)
def alternar_fixado(prompt_id: int, conn=Depends(get_db)):
    p = db.alternar_fixado(conn, prompt_id)
    if not p:
        raise HTTPException(404, "Prompt não encontrado.")
    conn.commit()
    return p


@router.post("/prompts/{prompt_id}/arquivos", response_model=list[ArquivoOut], status_code=201)
def anexar(
    prompt_id: int,
    arquivos: list[UploadFile] | None = File(None),
    conn=Depends(get_db),
):
    if not db.obter_prompt(conn, prompt_id):
        raise HTTPException(404, "Prompt não encontrado.")
    criados = anexar_uploads(conn, prompt_id, arquivos or [])
    if not criados:
        raise HTTPException(400, "Nenhum arquivo enviado.")
    conn.commit()
    return criados


@router.get("/prompts/{prompt_id}/arquivos/{arquivo_id}")
def baixar_arquivo(prompt_id: int, arquivo_id: int, conn=Depends(get_db)):
    arq = db.obter_arquivo(conn, prompt_id, arquivo_id)
    if not arq:
        raise HTTPException(404, "Arquivo não encontrado.")
    # Headers HTTP são latin-1: fallback ASCII + RFC 5987 para nomes com acento.
    nome_ascii = re.sub(r"[^A-Za-z0-9._-]", "_", arq["nome"]) or "arquivo.txt"
    return Response(
        content=arq["conteudo"],
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{nome_ascii}"; '
                f"filename*=UTF-8''{quote(arq['nome'])}"
            )
        },
    )


@router.delete("/prompts/{prompt_id}/arquivos/{arquivo_id}", status_code=204)
def excluir_arquivo(prompt_id: int, arquivo_id: int, conn=Depends(get_db)):
    if not db.excluir_arquivo(conn, prompt_id, arquivo_id):
        raise HTTPException(404, "Arquivo não encontrado.")
    conn.commit()
