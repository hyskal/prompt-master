#!/bin/bash
# Script para corrigir o proxy Nginx — Execute na VM2

set -e

echo "🔧 CORRIGINDO NGINX PROXY ROUTING..."
echo "===================================="

# Backup da config atual
sudo cp /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/default.backup.$(date +%Y%m%d-%H%M%S)
echo "✅ Backup criado"

# Remover o bloco /prompts/ antigo (se existir)
echo "Removendo bloco /prompts/ antigo..."
sudo sed -i '/location \/prompts\//,/^[[:space:]]*}/d' /etc/nginx/sites-enabled/default

# Adicionar o bloco CORRETO (com ^~ para evitar conflitos)
echo "Adicionando bloco correto..."
sudo sed -i '/^}/i\
    location ^~ /prompts/ {\
        proxy_pass http://127.0.0.1:5008/;\
        proxy_set_header Host $host;\
        proxy_set_header X-Real-IP $remote_addr;\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\
        proxy_set_header X-Forwarded-Proto $scheme;\
        add_header Access-Control-Allow-Origin "https://hyskal.github.io" always;\
        add_header Access-Control-Allow-Methods "GET, POST, PUT, PATCH, DELETE, OPTIONS" always;\
        add_header Access-Control-Allow-Headers "Content-Type, X-API-Key, x-api-key" always;\
        add_header Access-Control-Allow-Private-Network "true" always;\
        if ($request_method = OPTIONS) { return 204; }\
    }
' /etc/nginx/sites-enabled/default

# Verificar sintaxe
echo -e "\nVerificando sintaxe Nginx..."
sudo nginx -t

# Recarregar
echo "Recarregando Nginx..."
sudo systemctl reload nginx

echo -e "\n✅ NGINX CORRIGIDO COM SUCESSO!"
echo ""
echo "Testes rápidos:"
echo "1. Local (com chave):"
echo "   curl -H 'X-API-Key: prompt-master-chave-segura' http://localhost/prompts/api/health"
echo ""
echo "2. Via duckdns (com chave):"
echo "   curl -H 'X-API-Key: prompt-master-chave-segura' https://smtlab.duckdns.org/prompts/api/health"
echo ""
echo "Esperado em ambos: {\"status\":\"ok\",\"app\":\"prompt-master\"}"
