"""Acesso ao SQLite (stdlib, sem ORM)."""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = os.environ.get("DB_PATH") or str(Path(__file__).resolve().parents[1] / "prompts.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS prompts (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo    TEXT NOT NULL,
    prompt    TEXT NOT NULL,
    categoria TEXT NOT NULL DEFAULT 'Geral',
    tag1      TEXT,
    tag2      TEXT,
    tag3      TEXT,
    data      TEXT NOT NULL,
    fixado    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_prompts_categoria ON prompts(categoria);

CREATE TABLE IF NOT EXISTS arquivos (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id INTEGER NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    nome      TEXT NOT NULL,
    conteudo  TEXT NOT NULL,
    tamanho   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_arquivos_prompt ON arquivos(prompt_id);
"""


def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def get_db():
    """Dependency: uma conexão por request; rollback implícito (close sem commit)
    se a rota levantar exceção. Rotas de escrita comitam explicitamente ANTES de
    responder — o teardown desta dependency só roda depois que a resposta é
    enviada, e um commit apenas aqui criaria uma janela em que o cliente já tem
    o 2xx mas outro request ainda não enxerga os dados. check_same_thread=False
    porque rotas síncronas do FastAPI rodam em threadpool."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def row_para_dict(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    tags = [t for t in (row["tag1"], row["tag2"], row["tag3"]) if t]
    arquivos = [
        {"id": a["id"], "nome": a["nome"], "tamanho": a["tamanho"]}
        for a in conn.execute(
            "SELECT id, nome, tamanho FROM arquivos WHERE prompt_id = ? ORDER BY id",
            (row["id"],),
        )
    ]
    return {
        "id": row["id"],
        "titulo": row["titulo"],
        "prompt": row["prompt"],
        "categoria": row["categoria"],
        "tags": tags,
        "data": row["data"],
        "fixado": bool(row["fixado"]),
        "arquivos": arquivos,
    }


def listar_prompts(
    conn: sqlite3.Connection,
    categoria: str | None = None,
    q: str | None = None,
) -> list[dict]:
    conditions, params = [], []
    if categoria:
        conditions.append("categoria = ?")
        params.append(categoria)
    if q:
        like = f"%{q}%"
        conditions.append(
            "(titulo LIKE ? OR prompt LIKE ? OR tag1 LIKE ? OR tag2 LIKE ? OR tag3 LIKE ?)"
        )
        params.extend([like, like, like, like, like])
    sql = "SELECT * FROM prompts"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY fixado DESC, data DESC, id DESC"
    return [row_para_dict(conn, r) for r in conn.execute(sql, params)]


def duplicar_prompt(conn: sqlite3.Connection, prompt_id: int) -> dict | None:
    p = obter_prompt(conn, prompt_id)
    if not p:
        return None
    return inserir_prompt(
        conn, "Cópia de " + p["titulo"], p["prompt"], p["categoria"], p["tags"], agora_iso()
    )


def obter_prompt(conn: sqlite3.Connection, prompt_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,)).fetchone()
    return row_para_dict(conn, row) if row else None


def inserir_prompt(
    conn: sqlite3.Connection,
    titulo: str,
    prompt: str,
    categoria: str,
    tags: list[str],
    data: str,
    fixado: bool = False,
) -> dict:
    t = (list(tags) + [None, None, None])[:3]
    cur = conn.execute(
        "INSERT INTO prompts (titulo, prompt, categoria, tag1, tag2, tag3, data, fixado)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (titulo, prompt, categoria, t[0], t[1], t[2], data, int(fixado)),
    )
    return obter_prompt(conn, cur.lastrowid)


def excluir_prompt(conn: sqlite3.Connection, prompt_id: int) -> bool:
    return conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,)).rowcount > 0


def atualizar_prompt(
    conn: sqlite3.Connection,
    prompt_id: int,
    titulo: str,
    prompt: str,
    categoria: str,
    tags: list[str],
) -> dict | None:
    t = (list(tags) + [None, None, None])[:3]
    cur = conn.execute(
        "UPDATE prompts SET titulo=?, prompt=?, categoria=?, tag1=?, tag2=?, tag3=? WHERE id=?",
        (titulo, prompt, categoria, t[0], t[1], t[2], prompt_id),
    )
    if cur.rowcount == 0:
        return None
    return obter_prompt(conn, prompt_id)


def alternar_fixado(conn: sqlite3.Connection, prompt_id: int) -> dict | None:
    cur = conn.execute("UPDATE prompts SET fixado = 1 - fixado WHERE id = ?", (prompt_id,))
    if cur.rowcount == 0:
        return None
    return obter_prompt(conn, prompt_id)


def contar_prompts(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM prompts").fetchone()[0]


def contar_por_categoria(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    return [
        (r["categoria"], r["qtd"])
        for r in conn.execute(
            "SELECT categoria, COUNT(*) AS qtd FROM prompts"
            " GROUP BY categoria ORDER BY categoria COLLATE NOCASE"
        )
    ]


def apagar_todos(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM arquivos")
    conn.execute("DELETE FROM prompts")


def contar_arquivos(conn: sqlite3.Connection, prompt_id: int) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM arquivos WHERE prompt_id = ?", (prompt_id,)
    ).fetchone()[0]


def inserir_arquivo(conn: sqlite3.Connection, prompt_id: int, nome: str, conteudo: str) -> dict:
    tamanho = len(conteudo.encode("utf-8"))
    cur = conn.execute(
        "INSERT INTO arquivos (prompt_id, nome, conteudo, tamanho) VALUES (?, ?, ?, ?)",
        (prompt_id, nome, conteudo, tamanho),
    )
    return {"id": cur.lastrowid, "nome": nome, "tamanho": tamanho}


def obter_arquivo(conn: sqlite3.Connection, prompt_id: int, arquivo_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM arquivos WHERE id = ? AND prompt_id = ?", (arquivo_id, prompt_id)
    ).fetchone()


def excluir_arquivo(conn: sqlite3.Connection, prompt_id: int, arquivo_id: int) -> bool:
    return (
        conn.execute(
            "DELETE FROM arquivos WHERE id = ? AND prompt_id = ?", (arquivo_id, prompt_id)
        ).rowcount
        > 0
    )


def listar_arquivos_completos(conn: sqlite3.Connection, prompt_id: int) -> list[dict]:
    return [
        {"nome": a["nome"], "conteudo": a["conteudo"]}
        for a in conn.execute(
            "SELECT nome, conteudo FROM arquivos WHERE prompt_id = ? ORDER BY id",
            (prompt_id,),
        )
    ]
