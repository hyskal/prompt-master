# Roteiro Completo de Verificação — Agente Claude

**Objetivo:** Verificar que tudo funciona: GitHub Pages + API + Integração E2E  
**Tempo estimado:** 10-15 minutos

---

## 📋 **PARTE 1: Verificar GitHub Pages**

### 1.1 — Acessar a página

```bash
curl -s -I https://hyskal.github.io/prompt-master/ | head -5
```

**Esperado:**
```
HTTP/2 200
content-type: text/html
```

### 1.2 — Verificar se index.html está presente

```bash
curl -s https://hyskal.github.io/prompt-master/index.html | grep -o '<title>.*</title>'
```

**Esperado:**
```
<title>Prompt Master — seus prompts de IA</title>
```

### 1.3 — Verificar se os assets carregam (app.js, style.css)

```bash
echo "=== app.js ===" && curl -s -o /dev/null -w "%{http_code}\n" https://hyskal.github.io/prompt-master/app.js
echo "=== style.css ===" && curl -s -o /dev/null -w "%{http_code}\n" https://hyskal.github.io/prompt-master/style.css
```

**Esperado:**
```
200
200
```

### 1.4 — Verificar se o app.js tem a URL pré-configurada

```bash
curl -s https://hyskal.github.io/prompt-master/app.js | grep "URL_PADRAO"
```

**Esperado:**
```
const URL_PADRAO = "https://smtlab.duckdns.org/prompts";
```

---

## 📡 **PARTE 2: Verificar API (na VM2)**

### 2.1 — Conectar na VM2

```bash
ssh -i ~/.ssh/vm-oracle-smartlab ubuntu@146.235.43.123
# ou acesse via terminal do Oracle Cloud
```

### 2.2 — Verificar que o serviço está rodando

```bash
pmstatus
```

**Esperado:**
```
● prompt-master.service - Prompt Master API
   Loaded: loaded (/etc/systemd/system/prompt-master.service; enabled; vendor preset: enabled)
   Active: active (running) since ...
```

Se não estiver rodando:
```bash
pmstart
sleep 2
pmstatus
```

### 2.3 — Testar API diretamente (porta 5008)

```bash
# Sem chave (esperado 401)
curl -s http://localhost:5008/api/health

# Com chave (esperado sucesso)
curl -s -H 'X-API-Key: prompt-master-chave-segura' http://localhost:5008/api/health
```

**Esperado:**
```json
{"status":"ok","app":"prompt-master"}
```

### 2.4 — Verificar Nginx está proxyando

```bash
# Teste via localhost (Nginx)
curl -s -H 'X-API-Key: prompt-master-chave-segura' http://localhost/prompts/api/health
```

**Esperado:**
```json
{"status":"ok","app":"prompt-master"}
```

Se der **404**, execute o script de diagnóstico:
```bash
bash ~/prompt-master/diagnostico-nginx.sh
```

### 2.5 — Verificar que CORS headers estão corretos

```bash
curl -s -i -H 'Origin: https://hyskal.github.io' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: x-api-key' \
  -X OPTIONS http://localhost/prompts/api/prompts | grep -iE "access-control|HTTP"
```

**Esperado:**
```
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://hyskal.github.io
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, X-API-Key, x-api-key
```

---

## 🧪 **PARTE 3: Teste E2E Completo**

### 3.1 — Criar um prompt via API

```bash
curl -s -X POST https://smtlab.duckdns.org/prompts/api/prompts \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: prompt-master-chave-segura' \
  -d '{
    "titulo": "Teste E2E — Agente",
    "prompt": "Este é um prompt de teste criado pelo agente de verificação.\nDeve aparecer no portal.",
    "categoria": "Testes",
    "tags": ["e2e", "verificacao"]
  }' | python3 -m json.tool
```

**Esperado:**
```json
{
  "id": 1,
  "titulo": "Teste E2E — Agente",
  "prompt": "Este é um prompt de teste...",
  "categoria": "Testes",
  "tags": ["e2e", "verificacao"],
  "data": "2026-06-13T...",
  "fixado": false,
  "arquivos": []
}
```

**Guarde o `id` (provavelmente 1 se for o primeiro)**

### 3.2 — Listar prompts

```bash
curl -s -H 'X-API-Key: prompt-master-chave-segura' \
  https://smtlab.duckdns.org/prompts/api/prompts | python3 -m json.tool | head -40
```

**Esperado:**
```json
[
  {
    "id": 1,
    "titulo": "Teste E2E — Agente",
    "categoria": "Testes",
    ...
  }
]
```

### 3.3 — Anexar um arquivo ao prompt

```bash
# Criar um arquivo de teste
echo "print('Teste de anexo')" > /tmp/teste.py

# Anexar
curl -s -X POST https://smtlab.duckdns.org/prompts/api/prompts/1/arquivos \
  -H 'X-API-Key: prompt-master-chave-segura' \
  -F 'arquivos=@/tmp/teste.py' | python3 -m json.tool
```

**Esperado:**
```json
[
  {
    "id": 1,
    "nome": "teste.py",
    "tamanho": 25
  }
]
```

### 3.4 — Baixar o anexo

```bash
curl -s -H 'X-API-Key: prompt-master-chave-segura' \
  https://smtlab.duckdns.org/prompts/api/prompts/1/arquivos/1
```

**Esperado:** (conteúdo do arquivo)
```
print('Teste de anexo')
```

### 3.5 — Fixar o prompt

```bash
curl -s -X PATCH https://smtlab.duckdns.org/prompts/api/prompts/1/fixar \
  -H 'X-API-Key: prompt-master-chave-segura' | python3 -m json.tool | grep fixado
```

**Esperado:**
```
"fixado": true
```

### 3.6 — Exportar JSON

```bash
curl -s -H 'X-API-Key: prompt-master-chave-segura' \
  https://smtlab.duckdns.org/prompts/api/prompts/export \
  -o /tmp/backup.json

cat /tmp/backup.json | python3 -m json.tool | head -20
```

**Esperado:**
```json
{
  "versao": 1,
  "exportado_em": "2026-06-13T...",
  "total": 1,
  "prompts": [
    {
      "titulo": "Teste E2E — Agente",
      "arquivos": [
        {
          "nome": "teste.py",
          "conteudo": "print('Teste de anexo')\n"
        }
      ],
      ...
    }
  ]
}
```

### 3.7 — Deletar o prompt

```bash
curl -s -X DELETE https://smtlab.duckdns.org/prompts/api/prompts/1 \
  -H 'X-API-Key: prompt-master-chave-segura' \
  -o /dev/null -w "Status: %{http_code}\n"
```

**Esperado:**
```
Status: 204
```

### 3.8 — Verificar que foi deletado

```bash
curl -s -H 'X-API-Key: prompt-master-chave-segura' \
  https://smtlab.duckdns.org/prompts/api/prompts | python3 -m json.tool
```

**Esperado:** (lista vazia ou sem o prompt de teste)
```json
[]
```

---

## 🌐 **PARTE 4: Teste no Navegador (Manual)**

### 4.1 — Abrir o portal

```
https://hyskal.github.io/prompt-master/
```

### 4.2 — Verificar pré-preenchimento

- Campo "URL da API" deve estar com: `https://smtlab.duckdns.org/prompts`
- Campo "Chave de API" pode estar vazio (ou com a chave se desejar)

### 4.3 — Conectar

1. Clique no botão **"Conectar"**
2. Aguarde a lista carregar

**Esperado:** A lista de prompts aparece (vazia se foi deletada no teste anterior, ou com os prompts criados)

### 4.4 — Criar um novo prompt

1. Clique em **"➕ Novo prompt"**
2. Preencha:
   - **Título:** "Teste Portal"
   - **Categoria:** "Testes"
   - **Prompt:** "Teste criado via portal"
   - **Tags:** "portal, teste"
3. Clique em **"Salvar prompt"**

**Esperado:** Prompt aparece na lista, agrupado em "Testes"

### 4.5 — Copiar prompt

1. Procure o prompt criado
2. Clique em **"📋 Copiar"**
3. Rótulo muda para **"✅ Copiado!"**
4. Abra um editor de texto e cole (**Ctrl+V**)

**Esperado:** Texto do prompt aparece, com quebras de linha preservadas

### 4.6 — Fixar prompt

1. Clique em **"📌 Fixar"** no card do prompt
2. Verifique que o prompt vai para a seção **"📌 Fixados"** no topo

**Esperado:** Prompt sobe e aparece na seção especial

### 4.7 — Anexar arquivo

1. Clique em **"📎 Anexar"** no card
2. Selecione um arquivo `.md`, `.py` ou `.json`
3. O chip do arquivo aparece abaixo do título

**Esperado:** Arquivo listado com tamanho

### 4.8 — Baixar anexo

1. Clique no chip do arquivo (ex: "📄 teste.md")
2. Arquivo é baixado

**Esperado:** Arquivo aparece em Downloads

### 4.9 — Exportar JSON

1. Clique em **"⬇ Baixar JSON"** no topo
2. Arquivo `prompt-master-AAAA-MM-DD.json` é baixado

**Esperado:** JSON contém todos os prompts + anexos

### 4.10 — Filtrar por categoria

1. Clique no chip **"Testes"** abaixo dos chips
2. Lista mostra apenas prompts de "Testes"

**Esperado:** Apenas prompts daquela categoria aparecem

### 4.11 — Desconectar

1. Clique em **"Desconectar"** (topo direito)
2. Volta à tela de conexão com URL pré-preenchida

**Esperado:** Campo "URL da API" ainda tem `https://smtlab.duckdns.org/prompts`

---

## ✅ **Checklist Final**

- [ ] GitHub Pages está acessível e servindo HTML
- [ ] Assets (app.js, style.css) carregam com sucesso
- [ ] URL padrão está pré-configurada no app.js
- [ ] API responde na porta 5008 (com chave)
- [ ] Nginx está proxyando `/prompts/` corretamente
- [ ] CORS headers estão corretos
- [ ] Criar prompt funciona
- [ ] Listar prompts funciona
- [ ] Anexar arquivo funciona
- [ ] Baixar anexo funciona
- [ ] Fixar prompt funciona
- [ ] Exportar JSON funciona
- [ ] Deletar funciona
- [ ] Portal carrega com sucesso
- [ ] Conectar via portal funciona
- [ ] Criar/copiar/filtrar/exportar funcionam no navegador
- [ ] Desconectar volta à tela de conexão

---

## 🎯 **Se algum teste falhar:**

1. **Nginx 404:** Execute `bash ~/prompt-master/diagnostico-nginx.sh`
2. **API 401:** Verifique a chave em `~/prompt-master/backend/.env`
3. **Assets 404:** Verifique que o repo foi feito push corretamente
4. **Serviço caiu:** Execute `pmstart && pmlog`

---

**Pronto! Se todos os testes passarem, o sistema está 100% funcional! 🎉**
