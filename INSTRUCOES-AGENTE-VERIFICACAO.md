# 🔍 Instruções para o Agente — Verificar Repositório

**Problema:** GitHub Pages ainda mostra URL antiga (`https://smtlab.duckdns.org/prompts`) mesmo após atualizar o arquivo

**Solução:** Execute o script de verificação para diagnosticar o problema

---

## 📋 O que o Agente Deve Fazer

### Passo 1: Clonar/entrar no repositório

```bash
cd /home/user/prompt-master
# ou
git clone https://github.com/hyskal/prompt-master.git
cd prompt-master
```

### Passo 2: Executar o script de verificação

```bash
bash VERIFICACAO-REPO-AGENTE.sh
```

### Passo 3: Análise do Output

O script vai mostrar:

1. **STATUS GIT ATUAL** — branch, mudanças pendentes
2. **BRANCH ATUAL** — qual branch você está
3. **ÚLTIMO COMMIT** — qual foi o último commit
4. **CONTEÚDO DE docs/app.js** — se URL_PADRAO foi atualizado
5. **COMPARAÇÃO LOCAL vs REMOTO** — sincronização
6. **DIFERENÇAS ENTRE BRANCHES** — arquivos que diferem
7. **VERIFICAÇÃO NO GITHUB PAGES** — se main tem a atualização

### Passo 4: Baseado no resultado, executar UMA destas ações

#### **Cenário A: URL_PADRAO está em `claude/peaceful-carson-46sejz` mas NÃO em `main`**

Significa que o arquivo foi atualizado na branch feature, mas não foi feito merge para main (que é o que GitHub Pages serve).

**Solução:**
```bash
# Fazer merge da feature para main
git checkout main
git merge claude/peaceful-carson-46sejz
git push origin main
```

Depois aguarde 2-5 minutos para GitHub Pages recarregar.

#### **Cenário B: URL_PADRAO está em `main` mas portal ainda mostra URL antiga**

Significa que o arquivo está correto no repositório, mas GitHub Pages tem cache.

**Solução:**
```bash
# Forçar limpeza de cache do Pages
git commit --allow-empty -m "Limpar cache GitHub Pages"
git push origin main
```

Depois abra em **aba anônima/privada** e acesse:
```
https://hyskal.github.io/prompt-master/
```

#### **Cenário C: URL_PADRAO não está em lugar nenhum**

Significa que o commit não foi bem-sucedido ou foi perdido.

**Solução:**
```bash
# Verificar se o arquivo local tem a mudança
grep "smlapi" docs/app.js

# Se sim, re-fazer o push forçado
git add docs/app.js
git commit -m "Corrigir URL padrão para smlapi.duckdns.org"
git push -u origin claude/peaceful-carson-46sejz --force

# Depois fazer merge para main
git checkout main
git merge claude/peaceful-carson-46sejz
git push origin main
```

---

## 🎯 Comandos Rápidos para o Agente

```bash
# Ver conteúdo exato do arquivo
cat docs/app.js | grep -A2 "URL_PADRAO"

# Ver se está commitado
git log --oneline -5 docs/app.js

# Ver se está em main
git show main:docs/app.js | grep "URL_PADRAO"

# Ver se está em origin
git show origin/main:docs/app.js | grep "URL_PADRAO"

# Fazer merge e push rápido (se ainda não feito)
git checkout main && git merge claude/peaceful-carson-46sejz && git push origin main
```

---

## ✅ Verificação Final

Após executar as ações acima, o agente deve confirmar:

1. ✅ `docs/app.js` contém `URL_PADRAO = "https://smlapi.duckdns.org/prompts"`
2. ✅ Commit foi feito em `claude/peaceful-carson-46sejz`
3. ✅ Arquivo foi pushado para `origin/claude/peaceful-carson-46sejz`
4. ✅ Arquivo foi mergeado para `main`
5. ✅ `main` foi pushado para `origin/main`

Depois o portal em **https://hyskal.github.io/prompt-master/** deve mostrar a URL correta pré-preenchida.

---

## 📞 Se o Agente Tiver Dúvidas

- Executar `git status` para ver estado atual
- Executar `git log --oneline -10` para ver histórico recente
- Executar `git diff main..HEAD` para ver o que mudou
