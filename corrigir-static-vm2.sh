#!/bin/bash
# Corrige o problema: https://smlapi.duckdns.org/prompts/ servia o frontend
# estático em vez da API. Fix: desativar static files no FastAPI (o frontend
# já está no GitHub Pages; a VM2 só precisa servir /api/* e /ui/*).

set -e

ENV_FILE="/home/ubuntu/prompt-master/backend/.env"

echo "=== Corrigindo DOCS_DIR no .env ==="

if grep -q "^DOCS_DIR=" "$ENV_FILE" 2>/dev/null; then
    sed -i 's|^DOCS_DIR=.*|DOCS_DIR=|' "$ENV_FILE"
    echo "✅ DOCS_DIR atualizado para vazio"
else
    echo "DOCS_DIR=" >> "$ENV_FILE"
    echo "✅ DOCS_DIR adicionado (vazio)"
fi

echo ""
echo "=== Conteúdo do .env ==="
cat "$ENV_FILE"

echo ""
echo "=== Reiniciando serviço ==="
sudo systemctl restart prompt-master
sleep 2
sudo systemctl status prompt-master --no-pager | head -5

echo ""
echo "=== Verificando endpoints ==="
echo ""
echo "Raiz / (deve retornar JSON, não HTML):"
curl -s http://localhost:5008/ | head -1

echo ""
echo "API health (deve retornar {\"status\":\"ok\"}):"
curl -s -H "X-API-Key: masterapi99!" http://localhost:5008/api/health

echo ""
echo "Via Nginx /prompts/ (deve retornar JSON):"
curl -s http://localhost/prompts/

echo ""
echo "Via HTTPS /prompts/api/health:"
curl -s -H "X-API-Key: masterapi99!" https://smlapi.duckdns.org/prompts/api/health

echo ""
echo "=== PRONTO ==="
echo "Acesse https://hyskal.github.io/prompt-master/ e clique Conectar com:"
echo "  URL: https://smlapi.duckdns.org/prompts"
echo "  Chave: masterapi99!"
