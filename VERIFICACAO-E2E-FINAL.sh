#!/bin/bash
# Verificação E2E Final — Execute na VM2 para diagnosticar conexão

set -e

echo "🔍 VERIFICAÇÃO E2E COMPLETA — Prompt Master"
echo "=============================================="
echo ""

API_KEY="masterapi99!"
DOMINIO="smlapi.duckdns.org"
IP="146.235.43.123"
PORTA="5008"

echo "📋 CONFIGURAÇÃO ESPERADA:"
echo "========================"
echo "Domínio: $DOMINIO"
echo "IP: $IP"
echo "Porta: $PORTA"
echo "API Key: $API_KEY"
echo ""

# ============================================================================
# PARTE 1: VERIFICAÇÕES NA VM2 (Oracle)
# ============================================================================

echo "✅ PARTE 1: VERIFICAÇÕES NA VM2 (Oracle)"
echo "=========================================="
echo ""

echo "1️⃣ Status do Serviço"
echo "===================="
sudo systemctl status prompt-master --no-pager | head -8
echo ""

echo "2️⃣ Porta 5008 Listening?"
echo "========================"
ss -tlnp 2>/dev/null | grep 5008 || echo "❌ Porta não está listening"
echo ""

echo "3️⃣ Teste Direto na API (porta 5008)"
echo "===================================="
echo "Sem chave (esperado 401):"
curl -s http://localhost:5008/api/health -w "\nStatus: %{http_code}\n" || echo "❌ Erro"
echo ""

echo "Com chave:"
curl -s -H "X-API-Key: $API_KEY" http://localhost:5008/api/health -w "\nStatus: %{http_code}\n" || echo "❌ Erro"
echo ""

echo "4️⃣ Teste via Nginx (localhost)"
echo "==============================="
curl -s -H "X-API-Key: $API_KEY" http://localhost/prompts/api/health -w "\nStatus: %{http_code}\n" || echo "❌ Erro"
echo ""

echo "5️⃣ Teste via IP Direto (sem HTTPS)"
echo "==================================="
curl -s -H "X-API-Key: $API_KEY" http://127.0.0.1:5008/api/health -w "\nStatus: %{http_code}\n" || echo "❌ Erro"
echo ""

echo "6️⃣ Teste HTTPS via duckdns (ignore SSL error)"
echo "=============================================="
curl -s -k -H "X-API-Key: $API_KEY" https://$DOMINIO/prompts/api/health -w "\nStatus: %{http_code}\n" || echo "❌ Erro de conexão"
echo ""

echo "7️⃣ Verificar Resolução DNS"
echo "==========================="
dig +short $DOMINIO || echo "❌ DNS falhou"
nslookup $DOMINIO 2>/dev/null | tail -2 || echo "ℹ️ dig/nslookup indisponível"
echo ""

echo "8️⃣ Verificar Certificado SSL"
echo "============================="
openssl s_client -connect $DOMINIO:443 -servername $DOMINIO < /dev/null 2>/dev/null | grep -A 2 "subject=" || echo "⚠️ Certificado não encontrado"
echo ""

echo "9️⃣ Config Nginx - Location /prompts/"
echo "===================================="
sudo grep -A 15 "location" /etc/nginx/sites-enabled/default 2>/dev/null | grep -A 10 "/prompts/" || echo "❌ Location não encontrada"
echo ""

echo "🔟 CORS Headers - Preflight Test"
echo "================================"
curl -s -i -X OPTIONS http://localhost/prompts/api/prompts \
  -H "Origin: https://hyskal.github.io" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: x-api-key" 2>/dev/null | grep -i "access-control" || echo "❌ CORS headers não encontrados"
echo ""

# ============================================================================
# PARTE 2: TESTES PARA O NAVEGADOR
# ============================================================================

echo ""
echo "✅ PARTE 2: INSTRUÇÕES PARA TESTE NO NAVEGADOR"
echo "=============================================="
echo ""

echo "📌 URLs para testar:"
echo "===================="
echo ""
echo "1. API via IP direto (sem SSL, http):"
echo "   http://146.235.43.123:5008/api/health"
echo "   Header: X-API-Key: $API_KEY"
echo ""

echo "2. API via Nginx (localhost, http):"
echo "   http://localhost/prompts/api/health"
echo "   Header: X-API-Key: $API_KEY"
echo ""

echo "3. API via duckdns (https, ignorar SSL error):"
echo "   https://$DOMINIO/prompts/api/health"
echo "   Header: X-API-Key: $API_KEY"
echo ""

echo "4. Portal GitHub Pages:"
echo "   https://hyskal.github.io/prompt-master/"
echo "   Conectar com:"
echo "   - URL: https://$DOMINIO/prompts"
echo "   - Chave: $API_KEY"
echo ""

# ============================================================================
# PARTE 3: DIAGNÓSTICO AUTOMÁTICO
# ============================================================================

echo ""
echo "✅ DIAGNÓSTICO AUTOMÁTICO"
echo "========================="
echo ""

# Testar porta 5008
if ss -tlnp 2>/dev/null | grep -q 5008; then
    echo "✅ Porta 5008 está aberta"
else
    echo "❌ Porta 5008 NÃO está aberta"
fi

# Testar API direto
if curl -s -H "X-API-Key: $API_KEY" http://localhost:5008/api/health | grep -q "ok"; then
    echo "✅ API responde via porta 5008"
else
    echo "❌ API NÃO responde via porta 5008"
fi

# Testar Nginx
if curl -s -H "X-API-Key: $API_KEY" http://localhost/prompts/api/health | grep -q "ok"; then
    echo "✅ Nginx está proxyando corretamente"
else
    echo "❌ Nginx NÃO está proxyando"
fi

# Testar DNS
if dig +short $DOMINIO 2>/dev/null | grep -q "146.235.43.123"; then
    echo "✅ DNS aponta para VM2 (146.235.43.123)"
else
    echo "⚠️ DNS pode não estar resolvendo para VM2"
fi

echo ""
echo "=============================================="
echo "🎯 PRÓXIMO PASSO:"
echo "=============================================="
echo ""
echo "1. Se API responde via porta 5008: ✅"
echo "2. Se Nginx está proxyando: ✅"
echo "3. Se DNS aponta para VM2: ✅"
echo ""
echo "Então o problema é de CERTIFICADO SSL ou CORS"
echo ""
echo "SOLUÇÃO:"
echo "--------"
echo "No navegador:"
echo "1. Abra: https://hyskal.github.io/prompt-master/"
echo "2. Cole URL: https://$DOMINIO/prompts"
echo "3. Cole Chave: $API_KEY"
echo "4. Clique em Conectar"
echo ""
echo "Se der erro de SSL:"
echo "- Certificado pode estar para domínio antigo"
echo "- Executar: sudo certbot renew"
echo ""
