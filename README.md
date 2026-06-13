# ⚡ Prompt Master

Portal de prompts para IA: organize por **categoria**, **copie com um clique**, **edite inline**, **fixe** os favoritos, anexe **até 5 arquivos** por prompt, exporte prompts individuais como **JSON pronto para IA** e faça backup com **export/import em lote**.

- **Frontend**: página estática em [HTMX](https://htmx.org) (pasta [`docs/`](docs/)), publicada no **GitHub Pages**.
- **Backend**: API em [FastAPI](https://fastapi.tiangolo.com) (pasta [`backend/`](backend/)) com SQLite.

Ao abrir o portal, você informa a **URL da sua API** (e a chave, se houver). A escolha fica salva no navegador. Um mesmo portal publicado pode conversar com a API rodando na sua máquina ou num servidor.

Cada prompt guarda: **texto, título, data (automática), categoria e até 3 tags** — além dos anexos.

---

## Sumário

- [Rodando localmente](#rodando-localmente)
- [Deploy: Frontend no GitHub Pages](#deploy-frontend-no-github-pages)
- [Deploy: Backend em servidor Linux (Nginx + systemd)](#deploy-backend-em-servidor-linux-nginx--systemd)
- [Deploy: Docker (Render, Railway)](#deploy-docker-render-railway)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [A API](#a-api)
- [Resolução de problemas](#resolução-de-problemas)

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

Abra <http://localhost:8000> — o backend também serve o frontend. Na tela inicial, conecte-se com `http://localhost:8000`.

A documentação interativa da API (Swagger) fica em <http://localhost:8000/docs>.

---

## Deploy: Frontend no GitHub Pages

1. No repositório: **Settings → Pages**.
2. Em *Build and deployment*, escolha **Deploy from a branch**.
3. Branch `main`, pasta **`/docs`** → *Save*.
4. O portal fica em `https://SEU-USUARIO.github.io/prompt-master/`.

Para pré-preencher a URL da API, edite a constante em `docs/app.js`:

```js
const URL_PADRAO = "https://sua-api.exemplo.com/prompts";
```

> O frontend usa caminhos relativos, então funciona no subcaminho do Pages sem ajustes.

---

## Deploy: Backend em servidor Linux (Nginx + systemd)

Instruções testadas em **Ubuntu 24.04** (Oracle Cloud / qualquer VPS).

### 1. Pré-requisitos

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx

# Abrir portas no firewall
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

Também abra a porta **443** no grupo de segurança do seu provedor (Oracle Security List, AWS Security Group, etc.).

### 2. Clonar e instalar

```bash
cd /home/ubuntu
git clone https://github.com/hyskal/prompt-master.git
cd prompt-master/backend

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

```bash
cat << 'EOF' > /home/ubuntu/prompt-master/backend/.env
API_KEY=sua-chave-secreta
CORS_ORIGINS=https://SEU-USUARIO.github.io
DB_PATH=/home/ubuntu/prompt-master/backend/prompts.db
PORT=5008
DOCS_DIR=
EOF
```

> `DOCS_DIR=` vazio desativa os arquivos estáticos no servidor — o frontend já está no GitHub Pages.

### 4. Serviço systemd

```bash
sudo bash -c 'cat << EOF > /etc/systemd/system/prompt-master.service
[Unit]
Description=Prompt Master API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/prompt-master/backend
EnvironmentFile=/home/ubuntu/prompt-master/backend/.env
ExecStart=/home/ubuntu/prompt-master/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 5008
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF'

sudo systemctl daemon-reload
sudo systemctl enable prompt-master
sudo systemctl start prompt-master
sudo systemctl status prompt-master
```

### 5. Certificado SSL (Let's Encrypt)

```bash
sudo certbot certonly --nginx -d seu-dominio.duckdns.org
```

### 6. Nginx — proxy reverso

```bash
sudo bash -c 'cat << "EOF" > /etc/nginx/sites-available/prompt-master
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name seu-dominio.duckdns.org;

    ssl_certificate /etc/letsencrypt/live/seu-dominio.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seu-dominio.duckdns.org/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location ^~ /prompts/ {
        proxy_pass http://127.0.0.1:5008/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    listen [::]:80;
    server_name seu-dominio.duckdns.org;
    return 301 https://$server_name$request_uri;
}
EOF'

sudo ln -s /etc/nginx/sites-available/prompt-master /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

> **Não adicione** headers `Access-Control-*` no Nginx. O FastAPI (CORSMiddleware) já os envia; duplicar causa erro de CORS no browser.

### 7. Verificar

```bash
# Health check via HTTPS
curl -H 'X-API-Key: sua-chave-secreta' \
  https://seu-dominio.duckdns.org/prompts/api/health
# Esperado: {"status":"ok","app":"prompt-master"}
```

### Aliases úteis

Adicione ao `~/.bashrc`:

```bash
alias pmstart='sudo systemctl start prompt-master'
alias pmstop='sudo systemctl stop prompt-master'
alias pmrestart='sudo systemctl restart prompt-master'
alias pmstatus='sudo systemctl status prompt-master'
alias pmlog='sudo journalctl -u prompt-master -f'
alias pmupdate='cd /home/ubuntu/prompt-master && git pull && sudo systemctl restart prompt-master'
```

---

## Deploy: Docker (Render, Railway)

```bash
docker build -f backend/Dockerfile -t prompt-master .
docker run -p 8000:8000 -v prompt-master-dados:/data \
  -e API_KEY=sua-chave -e CORS_ORIGINS=https://SEU-USUARIO.github.io \
  prompt-master
```

No **Render**/**Railway**: crie um serviço web usando o `backend/Dockerfile` (contexto de build = raiz do repo).

- **1 instância** (SQLite não é multi-processo).
- **Disco persistente em `/data`** — sem ele, o banco é apagado a cada deploy.
- Health check: rota `GET /` (sem autenticação quando `DOCS_DIR` não está vazio).

---

## Variáveis de ambiente

| Variável | Default | Descrição |
|---|---|---|
| `API_KEY` | *(vazia)* | Todos os endpoints exigem `X-API-Key` se definida. |
| `CORS_ORIGINS` | `*` | Origens permitidas separadas por vírgula. Ex: `https://hyskal.github.io` |
| `DB_PATH` | `backend/prompts.db` | Caminho do SQLite. |
| `DOCS_DIR` | *(auto)* | Pasta do frontend. Deixe vazio no servidor para desativar static files. |
| `PORT` | `8000` | Porta do uvicorn (usado no Dockerfile). |

---

## Funcionalidades do portal

| Botão | Ação |
|---|---|
| 📋 **Copiar** | Copia o texto do prompt para o clipboard. |
| 📦 **Exportar JSON** | Copia o JSON completo (prompt + conteúdo dos anexos) para o clipboard, pronto para colar em uma IA. Fallback automático para download se o clipboard for negado. |
| ✏️ **Editar** | Abre formulário inline para editar título, categoria, tags e texto. |
| 📌 **Fixar** | Mantém o prompt no topo da lista. |
| 📎 **Anexar** | Adiciona arquivos ao prompt (até 5). |
| 🗑 **Excluir** | Remove o prompt e seus anexos. |
| ⬇ **Baixar JSON** *(cabeçalho)* | Exporta todos os prompts em lote. |
| ⬆ **Importar JSON** | Importa prompts de um arquivo JSON. |

### Exportar JSON para IA

O botão **📦 Exportar JSON** gera um JSON que inclui um campo `_instrucao` no topo, orientando qualquer IA a executar o prompt ao receber o conteúdo:

```json
{
  "_instrucao": "Você recebeu um prompt exportado do Prompt Master. Execute o campo 'prompt' como instrução principal. Se houver itens em 'arquivos', o campo 'conteudo' de cada um é contexto adicional...",
  "prompts": [
    {
      "titulo": "Nome do prompt",
      "prompt": "Instrução principal...",
      "arquivos": [{ "nome": "contexto.md", "conteudo": "..." }]
    }
  ]
}
```

---

## A API

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/health` | Health check (requer auth). |
| `GET` | `/api/prompts?categoria=` | Lista (fixados primeiro, mais recentes depois). |
| `POST` | `/api/prompts` | Cria prompt. |
| `GET` | `/api/prompts/{id}` | Detalhe. |
| `PATCH` | `/api/prompts/{id}` | Atualiza título, texto, categoria e tags. |
| `DELETE` | `/api/prompts/{id}` | Exclui (remove anexos em cascata). |
| `PATCH` | `/api/prompts/{id}/fixar` | Alterna fixado. |
| `GET` | `/api/prompts/{id}/export` | Exporta prompt individual com anexos e instrução para IA. |
| `POST` | `/api/prompts/{id}/arquivos` | Anexa arquivos (multipart, campo `arquivos`). |
| `GET` | `/api/prompts/{id}/arquivos/{arq}` | Baixa anexo. |
| `DELETE` | `/api/prompts/{id}/arquivos/{arq}` | Exclui anexo. |
| `GET` | `/api/prompts/export` | Exporta todos em JSON (com anexos embutidos). |
| `POST` | `/api/prompts/import` | Importa JSON (`modo=mesclar\|substituir`). |

Os endpoints `/ui/...` devolvem **fragmentos HTML** para o HTMX — mesma lógica, outra apresentação.

### Anexos

- Até **5 arquivos por prompt**, **1 MB** cada, somente **texto UTF-8**.
- Extensões aceitas: `.md .txt .json .yaml .yml .toml .xml .csv .html .css .js .ts .jsx .tsx .py .ipynb .java .kt .c .cpp .cs .go .rs .rb .php .swift .sql .sh .bash .ps1 .bat .ini .cfg .conf`

### Exemplos com curl

```bash
# Criar prompt
curl -X POST https://sua-api.exemplo.com/prompts/api/prompts \
  -H 'X-API-Key: sua-chave' \
  -H 'Content-Type: application/json' \
  -d '{"titulo":"Revisor","prompt":"Revise o código...","categoria":"Programação","tags":["código"]}'

# Anexar arquivos
curl -X POST https://sua-api.exemplo.com/prompts/api/prompts/1/arquivos \
  -H 'X-API-Key: sua-chave' \
  -F arquivos=@exemplo.py -F arquivos=@notas.md

# Export / Import
curl -H 'X-API-Key: sua-chave' \
  https://sua-api.exemplo.com/prompts/api/prompts/export -o backup.json

curl -X POST https://sua-api.exemplo.com/prompts/api/prompts/import \
  -H 'X-API-Key: sua-chave' \
  -F arquivo=@backup.json -F modo=mesclar
```

### Formato do JSON de export/import

```json
{
  "versao": 1,
  "exportado_em": "2026-06-13T17:00:00+00:00",
  "total": 1,
  "prompts": [
    {
      "titulo": "Revisor de código",
      "prompt": "Revise o código a seguir...",
      "categoria": "Programação",
      "tags": ["código", "revisão"],
      "fixado": false,
      "arquivos": [{ "nome": "exemplo.py", "conteudo": "print('oi')\n" }]
    }
  ]
}
```

No import, também é aceita uma lista pura `[ {...}, {...} ]`. Os `id`s são ignorados; a importação é **atômica** (qualquer item inválido cancela tudo).

---

## Resolução de problemas

### CORS: header duplicado

Não adicione `add_header Access-Control-*` no Nginx. O FastAPI já gerencia CORS. Headers duplicados causam falha no browser com a mensagem: *"header contains multiple values"*.

### Nginx serve o frontend em vez da API

Certifique-se de que `DOCS_DIR=` (vazio) está no `.env` do servidor e reinicie o serviço:

```bash
sudo systemctl restart prompt-master
```

### Preflight OPTIONS bloqueado (sem CORS headers)

Remova qualquer bloco `if ($request_method = OPTIONS) { return 204; }` do Nginx. O FastAPI (CORSMiddleware) intercepta OPTIONS antes das rotas de autenticação e responde corretamente.

### HTTPS + mixed content

Páginas HTTPS (GitHub Pages) só acessam APIs HTTPS — exceto `http://localhost`. A API no servidor deve estar atrás de HTTPS (Nginx + Let's Encrypt).

### Renovar certificado SSL

```bash
sudo certbot renew
sudo systemctl reload nginx
```
