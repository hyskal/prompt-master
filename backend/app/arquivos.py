"""Regras de anexos e lógica compartilhada de upload/importação."""

import json
from pathlib import Path

from fastapi import HTTPException, UploadFile
from pydantic import ValidationError

from . import db
from .schemas import PromptIn

MAX_ARQUIVOS_POR_PROMPT = 5
MAX_TAMANHO_ARQUIVO = 1024 * 1024  # 1 MB por arquivo
MAX_IMPORT_BYTES = 10 * 1024 * 1024  # 10 MB para o JSON de importação

EXTENSOES_PERMITIDAS = {
    ".md", ".markdown", ".txt", ".json", ".yaml", ".yml", ".toml", ".xml", ".csv",
    ".html", ".htm", ".css", ".js", ".mjs", ".ts", ".jsx", ".tsx",
    ".py", ".ipynb", ".java", ".kt", ".c", ".h", ".cpp", ".hpp", ".cs",
    ".go", ".rs", ".rb", ".php", ".swift", ".sql", ".sh", ".bash",
    ".ps1", ".bat", ".ini", ".cfg", ".conf",
}

# Valor pronto para o atributo accept="" dos inputs de arquivo.
ACCEPT_HTML = ",".join(sorted(EXTENSOES_PERMITIDAS))


def validar_arquivo(nome: str, conteudo: bytes) -> tuple[str, str]:
    """Valida nome/extensão/tamanho/encoding e devolve (nome_sanitizado, texto)."""
    nome = Path(nome or "").name.strip()
    if not nome:
        raise HTTPException(400, "Arquivo sem nome.")
    extensao = Path(nome).suffix.lower()
    if extensao not in EXTENSOES_PERMITIDAS:
        raise HTTPException(
            400,
            f"Extensão não permitida em “{nome}”. Use formatos de texto/código "
            "(.md, .json, .js, .html, .py etc.).",
        )
    if len(conteudo) > MAX_TAMANHO_ARQUIVO:
        raise HTTPException(400, f"Arquivo muito grande: “{nome}” (máximo 1 MB).")
    try:
        texto = conteudo.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, f"“{nome}” não é um arquivo de texto UTF-8 válido.")
    return nome, texto


def anexar_uploads(conn, prompt_id: int, uploads: list[UploadFile]) -> list[dict]:
    """Valida e grava uma lista de uploads num prompt. Retorna os metadados criados.

    Inputs de arquivo vazios geram uma parte multipart sem filename — são ignorados.
    """
    uploads = [u for u in uploads if u.filename]
    if not uploads:
        return []
    existentes = db.contar_arquivos(conn, prompt_id)
    if existentes + len(uploads) > MAX_ARQUIVOS_POR_PROMPT:
        raise HTTPException(
            400,
            f"Limite de {MAX_ARQUIVOS_POR_PROMPT} arquivos por prompt "
            f"(este prompt já tem {existentes}).",
        )
    criados = []
    for u in uploads:
        conteudo = u.file.read(MAX_TAMANHO_ARQUIVO + 1)
        nome, texto = validar_arquivo(u.filename, conteudo)
        criados.append(db.inserir_arquivo(conn, prompt_id, nome, texto))
    return criados


def processar_import(conn, upload: UploadFile, modo: str) -> dict:
    """Importa um JSON (formato do export ou lista pura). Atômico: qualquer item
    inválido aborta com 400 e nada é gravado (o commit fica na dependency get_db)."""
    if modo not in ("mesclar", "substituir"):
        raise HTTPException(400, "Modo deve ser 'mesclar' ou 'substituir'.")
    bruto = upload.file.read(MAX_IMPORT_BYTES + 1)
    if len(bruto) > MAX_IMPORT_BYTES:
        raise HTTPException(400, "Arquivo de importação muito grande (máximo 10 MB).")
    try:
        dados = json.loads(bruto.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(400, "O arquivo enviado não é um JSON válido.")

    itens = dados.get("prompts") if isinstance(dados, dict) else dados
    if not isinstance(itens, list):
        raise HTTPException(
            400, "O JSON deve ser uma lista de prompts ou um export do Prompt Master."
        )

    if modo == "substituir":
        db.apagar_todos(conn)

    for i, item in enumerate(itens, start=1):
        if not isinstance(item, dict):
            raise HTTPException(400, f"Item {i} inválido: deve ser um objeto.")
        try:
            p = PromptIn(
                titulo=item.get("titulo", ""),
                prompt=item.get("prompt", ""),
                categoria=item.get("categoria") or "Geral",
                tags=item.get("tags") or [],
            )
        except ValidationError as e:
            erro = e.errors()[0]
            campo = ".".join(str(x) for x in erro.get("loc", ()))
            raise HTTPException(400, f"Item {i} inválido ({campo}): {erro.get('msg', 'erro')}")

        data = item.get("data")
        if not isinstance(data, str) or not data:
            data = db.agora_iso()
        criado = db.inserir_prompt(
            conn, p.titulo, p.prompt, p.categoria, p.tags, data, bool(item.get("fixado", False))
        )

        anexos = item.get("arquivos") or []
        if not isinstance(anexos, list) or len(anexos) > MAX_ARQUIVOS_POR_PROMPT:
            raise HTTPException(
                400,
                f"Item {i} inválido: máximo de {MAX_ARQUIVOS_POR_PROMPT} arquivos por prompt.",
            )
        for a in anexos:
            if not isinstance(a, dict) or not isinstance(a.get("conteudo"), str):
                raise HTTPException(
                    400, f"Item {i} inválido: anexo malformado (esperado nome + conteudo)."
                )
            nome, texto = validar_arquivo(str(a.get("nome", "")), a["conteudo"].encode("utf-8"))
            db.inserir_arquivo(conn, criado["id"], nome, texto)

    conn.commit()
    return {"importados": len(itens), "modo": modo, "total": db.contar_prompts(conn)}
