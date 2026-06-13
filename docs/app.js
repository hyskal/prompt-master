/* Prompt Master — lógica do portal estático.
 * O HTMX cuida das trocas de fragmentos; este arquivo cuida de:
 * conexão com a API (localStorage), reescrita de URLs relativas para a API
 * remota, header X-API-Key, cópia rápida, downloads e tratamento de erros. */
(function () {
  "use strict";

  const CHAVE_URL = "pm_api_url";
  const CHAVE_KEY = "pm_api_key";
  const MAX_ARQUIVOS = 5;
  const URL_PADRAO = "https://smlapi.duckdns.org/prompts"; // Pré-configurada; mude conforme necessário

  const $ = (sel) => document.querySelector(sel);
  const apiUrl = () => localStorage.getItem(CHAVE_URL) || "";
  const apiKey = () => localStorage.getItem(CHAVE_KEY) || "";

  function cabecalhos() {
    return apiKey() ? { "X-API-Key": apiKey() } : {};
  }

  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(el._timer);
    el._timer = setTimeout(() => { el.hidden = true; }, 3500);
  }

  function normalizarUrl(texto) {
    let url = (texto || "").trim();
    if (!url) return "";
    if (!/^https?:\/\//i.test(url)) {
      url = (/^(localhost|127\.0\.0\.1)/i.test(url) ? "http://" : "https://") + url;
    }
    return url.replace(/\/+$/, "");
  }

  function ehLocalhost(url) {
    return /^http:\/\/(localhost|127\.0\.0\.1)([:/]|$)/i.test(url);
  }

  function mostrarConexao(mensagem) {
    $("#app").hidden = true;
    $("#tela-conexao").hidden = false;
    // Pré-preencher com URL salva ou padrão
    $("#campo-url").value = apiUrl() || URL_PADRAO;
    const erro = $("#erro-conexao");
    erro.textContent = mensagem || "";
    erro.hidden = !mensagem;
  }

  function entrar() {
    $("#tela-conexao").hidden = true;
    $("#app").hidden = false;
    $("#status-api").textContent = "🔗 " + apiUrl();
    htmx.ajax("GET", "/ui/prompts", { target: "#lista", swap: "innerHTML" });
  }

  async function conectar(urlBruta, chave) {
    const url = normalizarUrl(urlBruta);
    if (!url) {
      mostrarConexao("Informe a URL da API.");
      return;
    }
    if (location.protocol === "https:" && url.startsWith("http://") && !ehLocalhost(url)) {
      mostrarConexao("Páginas HTTPS só acessam APIs HTTPS (exceto localhost). Use uma URL https://.");
      return;
    }
    const btn = $("#btn-conectar");
    btn.disabled = true;
    btn.textContent = "Conectando…";
    try {
      const resp = await fetch(url + "/api/health", {
        headers: chave ? { "X-API-Key": chave } : {},
        signal: AbortSignal.timeout(5000),
      });
      if (resp.status === 401) {
        mostrarConexao("Chave de API inválida ou ausente.");
        return;
      }
      if (!resp.ok) {
        mostrarConexao("Erro " + resp.status + " ao conectar à API.");
        return;
      }
      localStorage.setItem(CHAVE_URL, url);
      if (chave) localStorage.setItem(CHAVE_KEY, chave);
      else localStorage.removeItem(CHAVE_KEY);
      entrar();
    } catch (e) {
      mostrarConexao("Não foi possível conectar a " + url + ". Verifique a URL e se a API está no ar.");
    } finally {
      btn.disabled = false;
      btn.textContent = "Conectar";
    }
  }

  function sair() {
    $("#campo-url").value = apiUrl();
    $("#campo-chave").value = "";
    localStorage.removeItem(CHAVE_URL);
    localStorage.removeItem(CHAVE_KEY);
    mostrarConexao();
  }

  async function baixar(caminho, nomeArquivo) {
    try {
      const resp = await fetch(apiUrl() + caminho, { headers: cabecalhos() });
      if (resp.status === 401) {
        mostrarConexao("Chave de API inválida ou ausente.");
        return;
      }
      if (!resp.ok) {
        toast("Erro " + resp.status + " ao baixar o arquivo.");
        return;
      }
      const blob = await resp.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = nomeArquivo;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      toast("Não foi possível baixar o arquivo.");
    }
  }

  function copiarPrompt(botao) {
    const texto = botao.closest(".card").querySelector(".texto").textContent;
    navigator.clipboard.writeText(texto).then(() => {
      const original = botao.textContent;
      botao.textContent = "✅ Copiado!";
      botao.disabled = true;
      setTimeout(() => {
        botao.textContent = original;
        botao.disabled = false;
      }, 1500);
    }).catch(() => toast("Não foi possível copiar para a área de transferência."));
  }

  /* ---------- HTMX: requests cross-origin para a API conectada ---------- */

  // Os atributos hx-* usam caminhos relativos (/ui/...): aqui eles ganham o
  // prefixo da API salva e o header da chave. URLs absolutas passam intactas.
  document.addEventListener("htmx:configRequest", (e) => {
    if (!/^https?:\/\//i.test(e.detail.path)) {
      const caminho = e.detail.path.startsWith("/") ? e.detail.path : "/" + e.detail.path;
      e.detail.path = apiUrl() + caminho;
    }
    if (apiKey()) e.detail.headers["X-API-Key"] = apiKey();
  });

  // Falha de rede no meio da sessão: volta à tela de conexão (mantém a URL salva).
  document.addEventListener("htmx:sendError", () => {
    toast("API inacessível.");
    mostrarConexao("A API ficou inacessível. Conecte-se novamente.");
  });

  document.addEventListener("htmx:responseError", (e) => {
    const xhr = e.detail.xhr;
    if (xhr.status === 401) {
      mostrarConexao("Chave de API inválida ou ausente.");
      return;
    }
    let msg = xhr.responseText || "";
    try { msg = JSON.parse(msg).detail || msg; } catch (_) { /* texto puro */ }
    if (typeof msg !== "string") msg = JSON.stringify(msg);
    toast("Erro " + xhr.status + ": " + msg.slice(0, 200));
  });

  // Confirmação extra ao importar substituindo tudo.
  document.addEventListener("htmx:confirm", (e) => {
    const form = e.target.closest && e.target.closest("#form-importar");
    if (!form) return;
    const modo = form.querySelector('input[name="modo"]:checked');
    if (modo && modo.value === "substituir") {
      e.preventDefault();
      if (window.confirm("Isso apagará TODOS os prompts atuais antes de importar. Continuar?")) {
        e.detail.issueRequest(true);
      }
    }
  });

  /* ---------- Delegação de eventos (sobrevive aos swaps do HTMX) ---------- */

  document.addEventListener("click", (e) => {
    const copiar = e.target.closest(".btn-copiar");
    if (copiar) { copiarPrompt(copiar); return; }
    const baixarBtn = e.target.closest(".btn-baixar");
    if (baixarBtn) baixar(baixarBtn.dataset.url, baixarBtn.dataset.nome);
  });

  // Limite de arquivos validado também no cliente (o servidor é a autoridade).
  document.addEventListener("change", (e) => {
    const input = e.target;
    if (input.matches && input.matches('input[type="file"][name="arquivos"]') &&
        input.files.length > MAX_ARQUIVOS) {
      toast("Máximo de " + MAX_ARQUIVOS + " arquivos por prompt.");
      input.value = "";
    }
  });

  /* ---------- Inicialização (scripts com defer: DOM já está pronto) ---------- */

  $("#form-conexao").addEventListener("submit", (e) => {
    e.preventDefault();
    conectar($("#campo-url").value, $("#campo-chave").value.trim());
  });

  $("#btn-sair").addEventListener("click", sair);

  $("#btn-exportar").addEventListener("click", () => {
    const hoje = new Date().toISOString().slice(0, 10);
    baixar("/api/prompts/export", "prompt-master-" + hoje + ".json");
  });

  if (apiUrl()) {
    conectar(apiUrl(), apiKey()); // reconexão automática
  } else {
    mostrarConexao();
  }
})();
