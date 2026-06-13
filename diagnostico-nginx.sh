#!/bin/bash
# Script de diagnóstico — execute na VM2

set -e

echo "🔍 DIAGNÓSTICO PROMPT MASTER — Nginx + API"
echo "============================================"

echo -e "\n1️⃣ Serviço rodando?"
sudo systemctl status prompt-master --no-pager | head -5

echo -e "\n2️⃣ Porta 5008 escutando?"
ss -tlnp 2>/dev/null | grep 5008 || echo "❌ Não encontrada"

echo -e "\n3️⃣ Teste direto na API (sem auth — esperado 401):"
curl -s http://localhost:5008/api/health || echo "❌ Erro"

echo -e "\n4️⃣ Teste com chave (esperado 200 OK):"
curl -s -H 'X-API-Key: prompt-master-chave-segura' http://localhost:5008/api/health | python3 -m json.tool 2>/dev/null || echo "❌ Erro"

echo -e "\n5️⃣ Config Nginx (location /prompts/):"
sudo grep -A 12 "location /prompts" /etc/nginx/sites-enabled/default 2>/dev/null | head -15 || echo "❌ Não encontrada"

echo -e "\n6️⃣ Teste via Nginx (via localhost):"
curl -s -H 'X-API-Key: prompt-master-chave-segura' http://localhost/prompts/api/health 2>&1 | head -c 200 && echo || echo "❌ Erro"

echo -e "\n7️⃣ Sintaxe Nginx OK?"
sudo nginx -t

echo -e "\n8️⃣ Recarregar Nginx:"
sudo systemctl reload nginx && echo "✅ Recarregado"

echo -e "\n9️⃣ Verificar logs Nginx (últimas 5 linhas de erro):"
sudo tail -5 /var/log/nginx/error.log

echo -e "\n✅ Diagnóstico concluído!"
echo "Se algum teste falhou, verifique os logs:"
echo "  pmlog              # Logs do Prompt Master"
echo "  sudo tail /var/log/nginx/error.log  # Erros Nginx"
