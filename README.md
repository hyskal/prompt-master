# ⚡ Prompt Master

Portal de prompts para IA: organize por **categoria**, **copie com um clique**, **fixe** os favoritos, anexe **até 5 arquivos** por prompt e faça backup com **export/import em JSON**.

- **Frontend**: página estática em [HTMX](https://htmx.org) (pasta [`docs/`](docs/)), pensada para o **GitHub Pages**.
- **Backend**: API em [FastAPI](https://fastapi.tiangolo.com) (pasta [`backend/`](backend/)) com SQLite — carrega, salva e deleta os prompts.

Ao abrir o portal, você informa a **URL da sua API** (e a chave, se houver). A escolha fica salva no navegador e os prompts são carregados dela. Um mesmo portal publicado pode, portanto, conversar com a API rodando na sua máquina ou num servidor.

Cada prompt guarda: **texto, título, data (automática), categoria e até 3 tags** — além dos anexos.

---

## Rodando localmente

Requisitos: Python 3.11+.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abra <http://localhost:8000> — o backend também serve o frontend. Na tela inicial, conecte-se usando `http://localhost:8000`.

A documentação interativa da API (Swagger) fica em <http://localhost:8000/docs>.

## Variáveis de ambiente

| Variável | Default | Descrição |
|---|---|---|
| `API_KEY` | *(vazia)* | Se definida, todos os endpoints exigem o header `X-API-Key`. Informe a chave na tela de conexão do portal. |
| `CORS_ORIGINS` | `*` | Origens permitidas, separadas por vírgula. Para travar no seu portal: `https://SEU-USUARIO.github.io` (a origem **não** inclui o caminho `/prompt-master`). |
| `DB_PATH` | `backend/prompts.db` | Caminho do arquivo SQLite (`/data/prompts.db` na imagem Docker). |
| `DOCS_DIR` | *(auto)* | Pasta do frontend a servir na raiz (detectada automaticamente). |

## Publicando o frontend no GitHub Pages

1. No repositório: **Settings → Pages**.
2. Em *Build and deployment*, escolha **Deploy from a branch**.
3. Branch `main`, pasta **`/docs`** → *Save*.
4. O portal fica em `https://SEU-USUARIO.github.io/prompt-master/`.

> O frontend usa caminhos relativos, então funciona no subcaminho do Pages sem ajustes.

## Publicando o backend (Render, Railway etc.)

A imagem Docker embute frontend + backend e é o jeito mais simples:

```bash
docker build -f backend/Dockerfile -t prompt-master .
docker run -p 8000:8000 -v prompt-master-dados:/data prompt-master
```

No **Render**/**Railway**: crie um serviço web a partir do repositório usando o `backend/Dockerfile` (contexto de build = raiz do repo). Recomendações:

- **1 instância/worker** (SQLite com escrita não é multi-processo).
- **Disco persistente montado em `/data`** — sem ele, o `prompts.db` é apagado a cada deploy. Enquanto não tiver disco, use o **⬇ Baixar JSON** como backup e o **⬆ Importar** para restaurar.
- Health check: rota `/` (responde sem autenticação).
- Defina `API_KEY` se a API ficar exposta na internet.

### HTTPS, localhost e o aviso do Chrome

- O GitHub Pages é **HTTPS**, e páginas HTTPS **não acessam APIs `http://`** (mixed content) — **exceto `http://localhost`**, que é liberado. Ou seja: API remota precisa de HTTPS (Render/Railway já fornecem); API local funciona normalmente.
- Ao conectar o portal publicado a `http://localhost:8000`, o Chrome pode pedir permissão de **acesso à rede local** (Private Network Access). A API já responde ao preflight com `Access-Control-Allow-Private-Network: true`; basta aceitar o aviso.

---

## A API

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/health` | Teste de conexão (autenticado, valida URL + chave). |
| `GET` | `/api/prompts?categoria=` | Lista (fixados primeiro, depois mais recentes). |
| `POST` | `/api/prompts` | Cria. Corpo: `titulo`, `prompt`, `categoria`, `tags` (máx. 3). |
| `GET` | `/api/prompts/{id}` | Detalhe. |
| `DELETE` | `/api/prompts/{id}` | Exclui (e os anexos, em cascata). |
| `PATCH` | `/api/prompts/{id}/fixar` | Alterna o fixado. |
| `POST` | `/api/prompts/{id}/arquivos` | Anexa arquivos (multipart, campo `arquivos`). |
| `GET` | `/api/prompts/{id}/arquivos/{arq}` | Baixa um anexo. |
| `DELETE` | `/api/prompts/{id}/arquivos/{arq}` | Exclui um anexo. |
| `GET` | `/api/prompts/export` | Baixa tudo em JSON (com anexos embutidos). |
| `POST` | `/api/prompts/import` | Importa JSON (multipart: `arquivo` + `modo=mesclar\|substituir`). |

Já os endpoints `/ui/...` devolvem **fragmentos HTML** para o HTMX do portal — mesma lógica, outra apresentação.

### Anexos

- Até **5 arquivos por prompt**, **1 MB** cada, somente **texto UTF-8**.
- Extensões aceitas: `.md .markdown .txt .json .yaml .yml .toml .xml .csv .html .htm .css .js .mjs .ts .jsx .tsx .py .ipynb .java .kt .c .h .cpp .hpp .cs .go .rs .rb .php .swift .sql .sh .bash .ps1 .bat .ini .cfg .conf`

### Exemplos com curl

```bash
# Criar um prompt
curl -X POST http://localhost:8000/api/prompts \
  -H 'Content-Type: application/json' \
  -d '{"titulo":"Revisor de código","prompt":"Revise o código a seguir...","categoria":"Programação","tags":["código","revisão"]}'

# Anexar arquivos ao prompt 1
curl -X POST http://localhost:8000/api/prompts/1/arquivos \
  -F arquivos=@exemplo.py -F arquivos=@notas.md

# Exportar e importar
curl http://localhost:8000/api/prompts/export -o backup.json
curl -X POST http://localhost:8000/api/prompts/import -F arquivo=@backup.json -F modo=mesclar

# Com API_KEY definida
curl -H 'X-API-Key: minha-chave' http://localhost:8000/api/prompts
```

### Formato do JSON de export/import

```json
{
  "versao": 1,
  "exportado_em": "2026-06-12T18:00:00+00:00",
  "total": 1,
  "prompts": [
    {
      "titulo": "Revisor de código",
      "prompt": "Revise o código a seguir...",
      "categoria": "Programação",
      "tags": ["código", "revisão"],
      "data": "2026-06-12T17:55:00+00:00",
      "fixado": false,
      "arquivos": [{ "nome": "exemplo.py", "conteudo": "print('oi')\n" }]
    }
  ]
}
```

No import, também é aceita uma lista pura `[ {...}, {...} ]`. Os `id`s são ignorados; a importação é **atômica** (qualquer item inválido cancela tudo).
