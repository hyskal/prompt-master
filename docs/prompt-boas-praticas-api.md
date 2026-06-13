# Prompt: Boas Práticas para Projetos de API (FastAPI + Frontend Estático)

> Use este prompt ao iniciar um novo projeto de API com FastAPI, SQLite e frontend separado (GitHub Pages, Vercel, etc.).

---

Você está criando uma API com FastAPI. Aplique todas as boas práticas abaixo desde o início:

## Arquitetura

- Separe as rotas em dois grupos com prefixos distintos:
  - `/api/*` — endpoints REST (JSON), consumidos por clients externos e mobile
  - `/ui/*` — fragmentos HTML para HTMX (mesma lógica, resposta diferente)
- Declare rotas com nomes literais (ex: `/prompts/export`, `/prompts/import`) **antes** das rotas com parâmetros (`/prompts/{id}`). Se não fizer isso, strings como "export" serão interpretadas como inteiros e causarão 422.

## SQLite

- Ative WAL (Write-Ahead Log) na inicialização: `conn.execute("PRAGMA journal_mode=WAL")`
- Ative foreign keys **por conexão** (não persiste entre conexões): `conn.execute("PRAGMA foreign_keys=ON")`
- Use `ON DELETE CASCADE` nos relacionamentos do schema para deleção automática de registros dependentes
- Faça `conn.commit()` **antes** de retornar a resposta na rota. Se comitar apenas no teardown da dependency, há uma janela em que o cliente já recebeu 2xx mas outro request ainda não enxerga os dados

## CORS (regra mais importante)

- Configure CORS **em um único lugar**: use o `CORSMiddleware` do FastAPI
- **Nunca adicione** `add_header Access-Control-*` no Nginx. Headers duplicados causam a mensagem `"header contains multiple values"` e bloqueiam o browser
- **Nunca adicione** `if ($request_method = OPTIONS) { return 204; }` no Nginx. O FastAPI (CORSMiddleware) intercepta OPTIONS antes das rotas de autenticação e responde corretamente. Interceptar no Nginx devolve 204 sem os headers CORS e quebra o preflight
- Para suportar Chrome Private Network Access (localhost ↔ páginas HTTPS): cheque se `allow_private_network` existe na assinatura do `CORSMiddleware`; se não, adicione um middleware fallback que insere o header `Access-Control-Allow-Private-Network: true` nas respostas OPTIONS

## Nginx (proxy reverso)

Config mínima e correta para proxiar `/caminho/` → FastAPI na porta 5008:

```nginx
location ^~ /caminho/ {
    proxy_pass http://127.0.0.1:5008/;   # trailing slash remove o prefixo
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    # Sem add_header Access-Control-* aqui
    # Sem bloco if OPTIONS aqui
}
```

## Arquivos estáticos

- Use a variável de ambiente `DOCS_DIR` para controlar se o FastAPI serve o frontend:
  - Localmente: detecta automaticamente a pasta `docs/` e serve em `/`
  - No servidor: `DOCS_DIR=` (vazio) desativa — o frontend está no GitHub Pages/Vercel
- Se o FastAPI servir `docs/` na raiz e o Nginx proxiar `/app/` → FastAPI, acessar `/app/` devolverá o `index.html`, não a API. Desative os arquivos estáticos com `DOCS_DIR=`

## Autenticação

- Use `secrets.compare_digest` para comparar a API Key (resistente a timing attack)
- Injete como dependency no router: `include_router(router, dependencies=[Depends(exigir_api_key)])`
- O CORSMiddleware intercepta OPTIONS **antes** das dependencies — preflight não precisa de auth

## Upload de arquivos

- Valide com allowlist de extensões, não blocklist
- Valide encoding UTF-8 (tente decodificar; capture `UnicodeDecodeError`)
- Imponha limite de tamanho antes de persistir (1 MB por arquivo, 5 por entidade)
- Retorne 400 com mensagem descritiva para cada tipo de violação

## Import atômico

- Valide **todos** os itens primeiro; só insira se todos forem válidos
- Use `conn.rollback()` explícito no `except` para garantir reversão
- Aceite tanto o formato com envelope `{"prompts": [...]}` quanto lista pura `[...]`

## Export para IA

- Ao exportar um registro para ser colado em uma IA, inclua um campo `_instrucao` (ou `_instructions`) no topo do JSON:
  ```json
  {
    "_instrucao": "Execute o campo 'prompt' como instrução principal. Arquivos em 'arquivos[].conteudo' são contexto adicional. Ignore campos técnicos.",
    ...
  }
  ```
- AIs leem objetos em ordem e usarão o campo de instrução como contexto antes de processar o restante

## Frontend com HTMX cross-origin

Quando o frontend está em outro domínio (GitHub Pages) e precisa chamar a API:

```js
// Reescreve paths relativos para a URL da API salva + injeta X-API-Key
document.addEventListener("htmx:configRequest", (e) => {
  if (!/^https?:\/\//i.test(e.detail.path)) {
    e.detail.path = apiUrl() + (e.detail.path.startsWith("/") ? "" : "/") + e.detail.path;
  }
  if (apiKey()) e.detail.headers["X-API-Key"] = apiKey();
});
```

- Isso permite usar `hx-get="/ui/prompts"` no HTML e o JS resolve para a URL completa da API
- Páginas HTTPS só chamam APIs HTTPS — exceto `http://localhost`

## systemd

```ini
[Service]
EnvironmentFile=/caminho/.env       # carrega variáveis do .env
ExecStart=/caminho/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 5008
Restart=always
RestartSec=5
```

- Use `--host 127.0.0.1` (não `0.0.0.0`) quando o Nginx faz o proxy — não exponha a porta diretamente
- Use `EnvironmentFile` para separar config do código

## Checklist de deploy

- [ ] `DOCS_DIR=` (vazio) no `.env` do servidor
- [ ] `CORS_ORIGINS=https://seu-frontend.com` (origem sem path)
- [ ] Nginx sem `add_header Access-Control-*` e sem bloco `if OPTIONS`
- [ ] Certificado SSL válido para o domínio (Let's Encrypt)
- [ ] Porta da API **não** exposta publicamente (só Nginx na 443)
- [ ] Testar preflight: `curl -I -X OPTIONS https://dominio/api/health -H "Origin: https://seu-frontend.com"`
- [ ] Testar com chave válida e inválida
