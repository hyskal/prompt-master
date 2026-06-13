# Briefing para o Agente Claude (Chrome) — Deploy Prompt Master

**Objetivo:** Implantar a API Prompt Master na VM2 da Oracle (146.235.43.123)  
**Porta:** 5008  
**Data:** Junho 2026

---

## ⚠️ PRÉ-REQUISITO — Abrir porta na Security List da Oracle

**O usuário DEVE fazer isso antes de chamar o agente** — via console web da Oracle (não pode ser feito via SSH):

1. **Oracle Cloud Console** → **Networking** → **Virtual Cloud Networks** → sua VCN → **Security Lists**
2. Localize a **Security List** usada pela VM2 (146.235.43.123)
3. Clique em **Add Ingress Rule**:
   - **Source CIDR:** `0.0.0.0/0`
   - **Protocol:** `TCP`
   - **Destination Port Range:** `5008`
4. Clique em **Add Ingress Rule**

> Sem abrir a porta aqui, a API não será acessível de fora, mesmo que rode localmente na VM.

---

## Instruções para o Agente (SSH na VM2)

Conectar na VM2:
```bash
ssh -i ~/.ssh/vm-oracle-smartlab ubuntu@146.235.43.123
```

### 1️⃣ Abrir porta no firewall da VM

```bash
# UFW
sudo ufw allow 5008/tcp
sudo ufw status | grep 5008

# iptables (necessário na Oracle Ubuntu)
sudo iptables -I INPUT -p tcp --dport 5008 -j ACCEPT
sudo netfilter-persistent save
```

### 2️⃣ Clonar o repositório

```bash
cd ~
git clone https://github.com/hyskal/prompt-master.git
cd prompt-master
```

> Repositório público — não exige SSH key. Alternativamente, se quiser usar SSH key:
> ```bash
> git clone git@github.com:hyskal/prompt-master.git
> ```

### 3️⃣ Criar virtualenv e instalar dependências

```bash
cd ~/prompt-master/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4️⃣ Criar arquivo `.env`

```bash
cat > ~/prompt-master/backend/.env << 'EOF'
API_KEY=prompt-master-chave-segura
CORS_ORIGINS=https://hyskal.github.io
DB_PATH=/home/ubuntu/prompt-master/backend/prompts.db
EOF
```

> **Atenção:** Troque `prompt-master-chave-segura` por uma chave segura que o usuário definir. Essa chave será necessária no portal.

### 5️⃣ Testar antes de criar o serviço

```bash
cd ~/prompt-master/backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 5008
```

Esperado: mensagem de startup do uvicorn. Teste em outro terminal:
```bash
curl -s http://localhost:5008/api/health
```

Resposta esperada:
```json
{"status":"ok","app":"prompt-master"}
```

Após confirmar, pressione **Ctrl+C** para parar.

### 6️⃣ Criar serviço systemd (autostart)

```bash
sudo tee /etc/systemd/system/prompt-master.service << 'EOF'
[Unit]
Description=Prompt Master API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/prompt-master/backend
EnvironmentFile=/home/ubuntu/prompt-master/backend/.env
ExecStart=/home/ubuntu/prompt-master/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 5008 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable prompt-master
sudo systemctl start prompt-master
sleep 2
sudo systemctl status prompt-master
```

### 7️⃣ Adicionar aliases bash

```bash
cat >> ~/.bash_aliases << 'EOF'

# Prompt Master API (porta 5008)
alias pmstart='sudo systemctl start prompt-master'
alias pmstop='sudo systemctl stop prompt-master'
alias pmrestart='sudo systemctl restart prompt-master'
alias pmlog='sudo journalctl -u prompt-master -f'
alias pmupdate='cd ~/prompt-master && git pull && pmrestart && echo "Atualizado!"'
alias pmstatus='sudo systemctl status prompt-master'
EOF

source ~/.bash_aliases
```

### 8️⃣ Configurar Nginx (HTTPS via DuckDNS)

Adicionar bloco ao Nginx para expor a API em `https://smtlab.duckdns.org/prompts/`:

```bash
sudo nano /etc/nginx/sites-enabled/default
```

Cole este bloco **antes do `}`** final do bloco `server`:

```nginx
    location /prompts/ {
        proxy_pass http://127.0.0.1:5008/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        add_header Access-Control-Allow-Origin "https://hyskal.github.io" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, PATCH, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, X-API-Key, x-api-key" always;
        add_header Access-Control-Allow-Private-Network "true" always;
        if ($request_method = OPTIONS) { return 204; }
    }
```

Verificar e recarregar:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 9️⃣ Verificar que tudo funciona

```bash
# Direto na porta (local)
curl -s http://localhost:5008/api/health

# Via Nginx (HTTPS)
curl -s https://smtlab.duckdns.org/prompts/api/health

# Com API key
curl -s -H 'X-API-Key: prompt-master-chave-segura' https://smtlab.duckdns.org/prompts/api/health
```

Esperado em todos os casos: `{"status":"ok","app":"prompt-master"}`

### 🔟 (Opcional) Adicionar ao healthcheck

```bash
# Verificar script atual
cat ~/healthcheck.sh

# Adicionar linha de verificação da API
echo "curl -s https://smtlab.duckdns.org/prompts/api/health > /dev/null 2>&1 && echo 'PM OK' || echo 'PM FALHA'" >> ~/healthcheck-pm.sh
```

---

## Para o Usuário — Conectar no Portal

Após o agente implantar com sucesso, acesse o portal em:

**URL:** https://hyskal.github.io/prompt-master/

A página virá **pré-preenchida** com:

| Campo | Valor |
|-------|-------|
| **URL da API** | `https://smtlab.duckdns.org/prompts` |
| **Chave de API** | *(deixe em branco ou informe se tiver)* |

Se a API foi configurada com `API_KEY=prompt-master-chave-segura`, preencha:

| Campo | Valor |
|-------|-------|
| **URL da API** | `https://smtlab.duckdns.org/prompts` |
| **Chave de API** | `prompt-master-chave-segura` |

Clique em **Conectar** → Pronto! A lista de prompts carregará.

---

## Troubleshooting

### Erro: "Não foi possível conectar à API"

1. ✅ Verificar se a porta 5008 foi aberta na **Security List da Oracle**
2. ✅ Verificar se o serviço está rodando: `pmstatus`
3. ✅ Verificar logs: `pmlog`
4. ✅ Testar local: `curl http://localhost:5008/api/health`
5. ✅ Testar via Nginx: `curl https://smtlab.duckdns.org/prompts/api/health`

### Erro 401 (Chave de API inválida)

- Confirmar que `API_KEY` no `.env` coincide com o valor informado no portal
- Testar com curl: `curl -H 'X-API-Key: SEU_VALOR' https://smtlab.duckdns.org/prompts/api/health`

### Banco de dados zerado após restart

Esperado se a VM é free tier sem disco persistente. Fazer backup:
```bash
cp ~/prompt-master/backend/prompts.db ~/prompt-master/backend/prompts.db.backup
```

E importar via **⬆ Importar JSON** no portal.

---

## Referência de Aliases (VM2)

```bash
# Prompt Master
pmstart    # inicia o serviço
pmstop     # para o serviço
pmrestart  # reinicia
pmlog      # mostra logs em tempo real
pmupdate   # git pull + reinicia
pmstatus   # status do systemd

# Grocy (existentes)
flasklimsstart, flasklimslog, etc.
sislabstart, sislablog, etc.
mkdapistart, mkdapilog, etc.
```

---

## Próximos passos

1. ✅ Agente implanta a API
2. ✅ Usuário testa o portal
3. ⏳ (Opcional) Integrar o Prompt Master com outros sistemas (LIMS, SmartLab, etc.)
4. ⏳ (Futuro) Banco de dados persistente em disco da Oracle

---

**Sessão:** https://claude.ai/code/session_01DcoRg6VRN2pL7LREPcYUH9
