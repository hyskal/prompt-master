#!/bin/bash
# Script de Verificação do Repositório — Execute para diagnosticar o problema

set -e

echo "🔍 VERIFICAÇÃO COMPLETA DO REPOSITÓRIO"
echo "======================================"
echo ""

echo "1️⃣ STATUS GIT ATUAL"
echo "===================="
git status
echo ""

echo "2️⃣ BRANCH ATUAL"
echo "==============="
git branch -a
echo ""

echo "3️⃣ ÚLTIMO COMMIT"
echo "==============="
git log -1 --oneline --all
echo ""

echo "4️⃣ VERIFICAR SE docs/app.js FOI ATUALIZADO"
echo "==========================================="
echo "URL_PADRAO no arquivo local:"
grep "URL_PADRAO" docs/app.js || echo "❌ NÃO ENCONTRADO"
echo ""

echo "5️⃣ COMPARAR LOCAL vs REMOTO"
echo "============================"
git fetch origin
echo ""
echo "Branch local:"
git log -1 --oneline
echo ""
echo "Branch remota (origin/claude/peaceful-carson-46sejz):"
git log -1 --oneline origin/claude/peaceful-carson-46sejz
echo ""

echo "6️⃣ BRANCH MAIN vs FEATURE"
echo "========================="
echo "Main:"
git log -1 --oneline main
echo ""
echo "Feature (claude/peaceful-carson-46sejz):"
git log -1 --oneline claude/peaceful-carson-46sejz
echo ""

echo "7️⃣ DIFERENÇA ENTRE MAIN E FEATURE"
echo "=================================="
git diff --name-only main..claude/peaceful-carson-46sejz || echo "Sem diferenças ou branches desalinhadas"
echo ""

echo "8️⃣ VERIFICAR SE GITHUB PAGES ESTÁ SERVINDO MAIN"
echo "==============================================="
echo "Arquivo em main:"
git show main:docs/app.js | grep "URL_PADRAO" || echo "❌ NÃO ENCONTRADO EM MAIN"
echo ""

echo "9️⃣ ARQUIVOS AFETADOS"
echo "===================="
git log --oneline -10 --all
echo ""

echo "🔟 RESUMO"
echo "========"
echo ""
echo "✓ Repositório validado"
echo ""
echo "PRÓXIMOS PASSOS:"
echo "1. Se URL_PADRAO está em claude/peaceful-carson-46sejz mas não em main:"
echo "   → Fazer MERGE da PR #1 para trazer as mudanças para main"
echo ""
echo "2. Se URL_PADRAO está em main mas portal não mostra:"
echo "   → GitHub Pages pode ter cache — aguarde 5 minutos"
echo "   → Ou limpe cache do navegador (Ctrl+Shift+Delete)"
echo ""
echo "3. Se URL_PADRAO não está em lugar nenhum:"
echo "   → Houve problema no commit/push — re-executar:"
echo "   → git push origin claude/peaceful-carson-46sejz --force"
