// Funções compartilhadas por todas as telas (carregar ANTES do script de cada página).

// Escapa texto vindo do banco antes de colocar em innerHTML (evita injeção de HTML/XSS).
function esc(valor) {
  return String(valor ?? "").replace(/[&<>"']/g, c => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

// Formata número como moeda brasileira.
function brl(valor) {
  return Number(valor || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

// Formata "2026-10-20T14:35:00" como data e hora separadas.
function dataHora(iso) {
  const [data = "", hora = ""] = String(iso || "").split(/[T ]/);
  const [a, m, d] = data.split("-");
  return { data: `${d}/${m}/${a}`, hora: hora.slice(0, 5) };
}

// Chamada à API JSON. Lança Error(mensagem) quando a resposta não for sucesso.
// Se a sessão expirou (401), volta para a tela de login.
async function api(url, opcoes = {}) {
  const config = { credentials: "same-origin", headers: {}, ...opcoes };
  if (opcoes.body !== undefined && typeof opcoes.body !== "string") {
    config.body = JSON.stringify(opcoes.body);
    config.headers["Content-Type"] = "application/json";
  }
  let resp;
  try {
    resp = await fetch(url, config);
  } catch (e) {
    throw new Error("Não foi possível falar com o servidor. Verifique se o Flask está ativo.");
  }
  let dados = {};
  try { dados = await resp.json(); } catch (e) { /* resposta sem JSON */ }
  if (resp.status === 401 && !url.endsWith("/login")) {
    location.href = "/";
    throw new Error("Sessão expirada.");
  }
  if (!resp.ok || dados.sucesso === false) {
    throw new Error(dados.mensagem || `Erro ${resp.status}`);
  }
  return dados;
}

// Mensagem rápida no canto da tela (usa <div id="toast"> da página).
let _toastTimer;
function mostrarToast(mensagem) {
  const el = document.getElementById("toast");
  if (!el) { alert(mensagem); return; }
  el.textContent = mensagem;
  el.classList.add("show");
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove("show"), 3200);
}

// Botão "Sair" (presente nos dois layouts).
document.addEventListener("click", async e => {
  if (!e.target.closest("[data-logout]")) return;
  try { await api("/logout", { method: "POST" }); } catch (err) { /* segue para o login */ }
  location.href = "/";
});
