// Telas do layout principal: login, painel, produtos, categorias e fornecedores.
// (Depende de api.js: api, esc, brl, mostrarToast.)

document.addEventListener("DOMContentLoaded", () => {
  const $ = id => document.getElementById(id);

  // ---------------------------------------------------------- Login
  const loginForm = $("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async e => {
      e.preventDefault();
      const msg = $("login-message");
      msg.style.color = "";
      msg.textContent = "Verificando acesso...";
      try {
        await api("/login", {
          method: "POST",
          body: { email: $("email").value.trim(), senha: $("senha").value },
        });
        location.href = "/dashboard";
      } catch (err) {
        msg.textContent = err.message || "Falha no login.";
        msg.style.color = "#c34343";
      }
    });
  }

  // ---------------------------------------------------------- Busca genérica (filtra linhas já na tela)
  document.querySelectorAll("[data-search]").forEach(campo => {
    campo.addEventListener("input", () => {
      const termo = campo.value.toLowerCase();
      document.querySelectorAll("tbody tr[data-row], .category-card").forEach(el => {
        el.hidden = !el.textContent.toLowerCase().includes(termo);
      });
    });
  });

  // Diálogos: botão "Cancelar"
  document.querySelectorAll("[data-close-dialog]").forEach(b =>
    b.addEventListener("click", () => b.closest("dialog").close()));

  // ---------------------------------------------------------- Painel
  if ($("dash-stats")) {
    api("/api/dashboard").then(d => {
      $("stat-produtos").textContent = d.resumo.total_produtos;
      $("stat-fornecedores").textContent = d.resumo.total_fornecedores;
      $("stat-baixo").textContent = d.resumo.estoque_baixo;
      $("stat-mov").textContent = d.resumo.movimentacoes_hoje;
      $("low-stock-rows").innerHTML = d.estoque_baixo.length
        ? d.estoque_baixo.map(p => `<tr><td>${esc(p.nome)}</td><td>${esc(p.categoria)}</td>
            <td>${p.quantidade}</td><td><i class="low">Estoque baixo</i></td></tr>`).join("")
        : `<tr><td colspan="4" class="muted">Nenhum produto com estoque baixo.</td></tr>`;
    }).catch(err => mostrarToast(err.message));
  }

  // ---------------------------------------------------------- Produtos (lista)
  const corpoProdutos = $("product-rows");
  if (corpoProdutos) {
    let produtos = [];
    const filtroCat = $("category"), filtroEst = $("stock");

    const desenhar = () => {
      const cat = filtroCat.value, est = filtroEst.value;
      const lista = produtos.filter(p =>
        (!cat || String(p.id_categoria) === cat) && (!est || p.status_estoque === est));
      corpoProdutos.innerHTML = lista.length ? lista.map(p => `
        <tr data-row data-id="${p.id_produto}">
          <td>${esc(p.codigo)}</td><td><b>${esc(p.nome)}</b></td>
          <td>${esc(p.categoria)}</td><td>${esc(p.fornecedor)}</td>
          <td>${brl(p.preco)}</td>
          <td class="${p.status_estoque === "low" ? "orange" : ""}">${p.quantidade}</td>
          <td>${p.estoque_minimo}</td>
          <td><i class="${p.status_estoque === "low" ? "low" : "good"}">${p.status_estoque === "low" ? "Estoque Baixo" : "Em Estoque"}</i></td>
          <td><a class="edit" href="/produtos/${p.id_produto}/editar" title="Editar">✎</a>
              <button class="delete" data-del="${p.id_produto}" title="Excluir">▤</button></td>
        </tr>`).join("")
        : `<tr><td colspan="9" class="muted">Nenhum produto encontrado.</td></tr>`;
      $("product-count").textContent = `Mostrando ${lista.length} de ${produtos.length} produtos`;
    };

    Promise.all([api("/api/produtos"), api("/api/categorias")]).then(([p, c]) => {
      produtos = p.produtos;
      c.categorias.forEach(cat => filtroCat.add(new Option(cat.nome, cat.id_categoria)));
      desenhar();
    }).catch(err => mostrarToast(err.message));

    filtroCat.addEventListener("change", desenhar);
    filtroEst.addEventListener("change", desenhar);

    corpoProdutos.addEventListener("click", async e => {
      const btn = e.target.closest("[data-del]");
      if (!btn || !confirm("Excluir este produto?")) return;
      try {
        await api(`/api/produtos/${btn.dataset.del}`, { method: "DELETE" });
        produtos = produtos.filter(p => String(p.id_produto) !== btn.dataset.del);
        desenhar();
        mostrarToast("Produto excluído.");
      } catch (err) { mostrarToast(err.message); }
    });
  }

  // ---------------------------------------------------------- Produto (cadastro / edição)
  const formProduto = $("product-form");
  if (formProduto) {
    const idProduto = formProduto.dataset.id;
    const msg = $("product-message");

    const carregarSelects = Promise.all([api("/api/categorias"), api("/api/fornecedores")])
      .then(([c, f]) => {
        c.categorias.forEach(x => $("sel-categoria").add(new Option(x.nome, x.id_categoria)));
        f.fornecedores.forEach(x => $("sel-fornecedor").add(new Option(x.nome, x.id_fornecedor)));
      });

    carregarSelects.then(async () => {
      if (!idProduto) return;
      const { produto } = await api(`/api/produtos/${idProduto}`);
      const f = formProduto.elements;
      f.codigo.value = produto.codigo;
      f.nome.value = produto.nome;
      f.id_categoria.value = produto.id_categoria;
      f.id_fornecedor.value = produto.id_fornecedor;
      f.preco.value = produto.preco;
      f.quantidade.value = produto.quantidade;
      f.estoque_minimo.value = produto.estoque_minimo;
      f.descricao.value = produto.descricao || "";
    }).catch(err => { msg.textContent = err.message; msg.className = "error"; });

    formProduto.addEventListener("submit", async e => {
      e.preventDefault();
      const f = formProduto.elements;
      const corpo = {
        codigo: f.codigo.value.trim(), nome: f.nome.value.trim(),
        id_categoria: f.id_categoria.value, id_fornecedor: f.id_fornecedor.value,
        preco: f.preco.value, estoque_minimo: f.estoque_minimo.value,
        descricao: f.descricao.value.trim(),
      };
      if (!idProduto) corpo.quantidade = f.quantidade.value;
      msg.className = "muted"; msg.textContent = "Salvando...";
      try {
        await api(idProduto ? `/api/produtos/${idProduto}` : "/api/produtos",
          { method: idProduto ? "PUT" : "POST", body: corpo });
        location.href = "/produtos";
      } catch (err) { msg.textContent = err.message; msg.className = "error"; }
    });
  }

  // ---------------------------------------------------------- Categorias
  const grade = $("category-grid");
  if (grade) {
    const dlg = $("category-dialog"), form = $("category-form");
    const cores = ["", "purple", "green", "orange"], icones = ["◇", "▤", "⚒", "▦"];
    let categorias = [];

    const desenhar = () => {
      grade.innerHTML = categorias.length ? categorias.map((c, i) => `
        <article class="panel category-card" data-id="${c.id_categoria}">
          <span class="cat-icon ${cores[i % 4]}">${icones[i % 4]}</span>
          <i>${c.total_produtos} produto(s)</i>
          <h2>${esc(c.nome)}</h2><p>${esc(c.descricao || "Sem descrição.")}</p>
          <button class="secondary edit" data-edit="${c.id_categoria}">Editar</button>
          <button class="delete" data-del="${c.id_categoria}">Excluir</button>
        </article>`).join("") : `<p class="muted">Nenhuma categoria cadastrada.</p>`;
    };
    const carregar = () => api("/api/categorias").then(d => { categorias = d.categorias; desenhar(); })
      .catch(err => mostrarToast(err.message));
    carregar();

    const abrir = cat => {
      $("category-dialog-title").textContent = cat ? "Editar categoria" : "Nova categoria";
      form.elements.id.value = cat ? cat.id_categoria : "";
      form.elements.nome.value = cat ? cat.nome : "";
      form.elements.descricao.value = cat ? cat.descricao || "" : "";
      dlg.showModal();
    };
    $("btn-nova-categoria").addEventListener("click", () => abrir(null));

    grade.addEventListener("click", async e => {
      const ed = e.target.closest("[data-edit]"), del = e.target.closest("[data-del]");
      if (ed) abrir(categorias.find(c => String(c.id_categoria) === ed.dataset.edit));
      if (del && confirm("Excluir esta categoria?")) {
        try {
          await api(`/api/categorias/${del.dataset.del}`, { method: "DELETE" });
          mostrarToast("Categoria excluída."); carregar();
        } catch (err) { mostrarToast(err.message); }
      }
    });

    form.addEventListener("submit", async e => {
      e.preventDefault();
      const id = form.elements.id.value;
      try {
        await api(id ? `/api/categorias/${id}` : "/api/categorias", {
          method: id ? "PUT" : "POST",
          body: { nome: form.elements.nome.value.trim(), descricao: form.elements.descricao.value.trim() },
        });
        dlg.close(); mostrarToast("Categoria salva."); carregar();
      } catch (err) { mostrarToast(err.message); }
    });
  }

  // ---------------------------------------------------------- Fornecedores
  const corpoFornecedores = $("supplier-rows");
  if (corpoFornecedores) {
    const dlg = $("supplier-dialog"), form = $("supplier-form");
    let fornecedores = [];

    const desenhar = () => {
      corpoFornecedores.innerHTML = fornecedores.length ? fornecedores.map(f => `
        <tr data-row>
          <td>♧　<b>${esc(f.nome)}</b></td><td>${esc(f.cnpj || "—")}</td>
          <td>${esc(f.telefone || "—")}</td><td>${esc(f.email || "—")}</td>
          <td>${f.total_produtos}</td>
          <td><button class="edit" data-edit="${f.id_fornecedor}">✎</button>
              <button class="delete" data-del="${f.id_fornecedor}">▤</button></td>
        </tr>`).join("") : `<tr><td colspan="6" class="muted">Nenhum fornecedor cadastrado.</td></tr>`;
    };
    const carregar = () => api("/api/fornecedores").then(d => { fornecedores = d.fornecedores; desenhar(); })
      .catch(err => mostrarToast(err.message));
    carregar();

    const abrir = f => {
      $("supplier-dialog-title").textContent = f ? "Editar fornecedor" : "Novo fornecedor";
      const el = form.elements;
      el.id.value = f ? f.id_fornecedor : "";
      el.nome.value = f ? f.nome : "";
      el.cnpj.value = f ? f.cnpj || "" : "";
      el.telefone.value = f ? f.telefone || "" : "";
      el.email.value = f ? f.email || "" : "";
      dlg.showModal();
    };
    $("btn-novo-fornecedor").addEventListener("click", () => abrir(null));

    corpoFornecedores.addEventListener("click", async e => {
      const ed = e.target.closest("[data-edit]"), del = e.target.closest("[data-del]");
      if (ed) abrir(fornecedores.find(f => String(f.id_fornecedor) === ed.dataset.edit));
      if (del && confirm("Excluir este fornecedor?")) {
        try {
          await api(`/api/fornecedores/${del.dataset.del}`, { method: "DELETE" });
          mostrarToast("Fornecedor excluído."); carregar();
        } catch (err) { mostrarToast(err.message); }
      }
    });

    form.addEventListener("submit", async e => {
      e.preventDefault();
      const el = form.elements, id = el.id.value;
      try {
        await api(id ? `/api/fornecedores/${id}` : "/api/fornecedores", {
          method: id ? "PUT" : "POST",
          body: { nome: el.nome.value.trim(), cnpj: el.cnpj.value.trim(),
                  telefone: el.telefone.value.trim(), email: el.email.value.trim() },
        });
        dlg.close(); mostrarToast("Fornecedor salvo."); carregar();
      } catch (err) { mostrarToast(err.message); }
    });
  }

  // ---------------------------------------------------------- Usuários (somente administrador)
  const corpoUsuarios = $("user-rows");
  if (corpoUsuarios) {
    const dlg = $("user-dialog"), form = $("user-form"), erro = $("user-form-error");
    let usuarios = [];

    const desenhar = () => {
      corpoUsuarios.innerHTML = usuarios.length ? usuarios.map(u => `
        <tr data-row>
          <td>♙　<b>${esc(u.nome)}</b></td><td>${esc(u.email)}</td>
          <td><i class="${u.perfil === "ADMINISTRADOR" ? "good" : "info"}">${u.perfil === "ADMINISTRADOR" ? "Administrador" : "Funcionário"}</i></td>
          <td><button class="edit" data-edit="${u.id_usuario}" title="Editar">✎</button>
              <button class="delete" data-del="${u.id_usuario}" title="Excluir">▤</button></td>
        </tr>`).join("") : `<tr><td colspan="4" class="muted">Nenhum usuário cadastrado.</td></tr>`;
      $("user-count").textContent = `${usuarios.length} usuário(s) cadastrado(s)`;
    };
    const carregar = () => api("/api/usuarios").then(d => { usuarios = d.usuarios; desenhar(); })
      .catch(err => mostrarToast(err.message));
    carregar();

    const abrir = u => {
      const el = form.elements;
      $("user-dialog-title").textContent = u ? "Editar usuário" : "Novo usuário";
      el.id.value = u ? u.id_usuario : "";
      el.nome.value = u ? u.nome : "";
      el.email.value = u ? u.email : "";
      el.perfil.value = u ? u.perfil : "FUNCIONARIO";
      el.senha.value = "";
      el.senha.required = !u;
      el.senha.placeholder = u ? "Deixe vazio para manter a senha atual" : "Mínimo de 6 caracteres";
      $("user-password-hint").textContent = u ? "(opcional)" : "(obrigatória ao cadastrar)";
      erro.textContent = "";
      dlg.showModal();
    };
    $("btn-novo-usuario").addEventListener("click", () => abrir(null));

    corpoUsuarios.addEventListener("click", async e => {
      const ed = e.target.closest("[data-edit]"), del = e.target.closest("[data-del]");
      if (ed) abrir(usuarios.find(u => String(u.id_usuario) === ed.dataset.edit));
      if (del && confirm("Excluir este usuário?")) {
        try {
          await api(`/api/usuarios/${del.dataset.del}`, { method: "DELETE" });
          mostrarToast("Usuário excluído."); carregar();
        } catch (err) { mostrarToast(err.message); }
      }
    });

    form.addEventListener("submit", async e => {
      e.preventDefault();
      const el = form.elements, id = el.id.value;
      const corpo = { nome: el.nome.value.trim(), email: el.email.value.trim(), perfil: el.perfil.value };
      if (el.senha.value) corpo.senha = el.senha.value;
      try {
        await api(id ? `/api/usuarios/${id}` : "/api/usuarios", { method: id ? "PUT" : "POST", body: corpo });
        dlg.close(); mostrarToast(id ? "Usuário atualizado." : "Usuário cadastrado."); carregar();
      } catch (err) { erro.textContent = err.message; }
    });
  }

  // ---------------------------------------------------------- Entrada / Saída de estoque
  function configurarEstoque(entrada) {
    const form = $(entrada ? "stock-entry-form" : "stock-exit-form");
    if (!form) return;
    const prefixo = entrada ? "entry" : "exit";
    const produto = $(`${prefixo}-product`), qtd = $(`${prefixo}-quantity`), obs = $(`${prefixo}-notes`);
    const statProduto = $(`${prefixo}-product-stat`), statTotal = $(`${prefixo}-total-stat`);
    const disponivel = $("exit-available");

    const atualizar = () => {
      const op = produto.selectedOptions[0];
      const atual = Number(op?.dataset.quantity || 0), valor = Number(qtd.value || 0);
      statProduto.textContent = op?.value ? op.dataset.name : "Nenhum";
      if (!op?.value) {
        statTotal.textContent = "—";
        if (disponivel) disponivel.value = "Selecione um produto";
        return;
      }
      if (disponivel) disponivel.value = String(atual);
      statTotal.textContent = valor > 0 ? String(entrada ? atual + valor : atual - valor) : String(atual);
      statTotal.style.color = (!entrada && valor > atual) ? "#d34848" : "";
    };

    const carregarProdutos = manterId => api("/api/produtos").then(d => {
      produto.length = 1;
      d.produtos.forEach(p => {
        const o = new Option(`${p.nome} — ${entrada ? "estoque atual" : "disponível"}: ${p.quantidade}`, p.id_produto);
        o.dataset.quantity = p.quantidade; o.dataset.name = p.nome;
        produto.add(o);
      });
      if (manterId) produto.value = manterId;
      atualizar();
    }).catch(err => mostrarToast(err.message));
    carregarProdutos();

    produto.addEventListener("change", atualizar);
    qtd.addEventListener("input", atualizar);
    form.addEventListener("reset", () => setTimeout(atualizar));

    form.addEventListener("submit", async e => {
      e.preventDefault();
      const op = produto.selectedOptions[0];
      const atual = Number(op?.dataset.quantity || 0), valor = Number(qtd.value);
      if (!op?.value || !Number.isInteger(valor) || valor <= 0) {
        mostrarToast("Selecione um produto e informe uma quantidade inteira maior que zero."); return;
      }
      if (!entrada && valor > atual) { mostrarToast("Quantidade insuficiente em estoque."); return; }
      try {
        const r = await api(`/api/movimentacoes/${entrada ? "entrada" : "saida"}`, {
          method: "POST",
          body: { id_produto: Number(op.value), quantidade: valor, observacao: obs.value.trim() || null },
        });
        mostrarToast(`${r.mensagem} Novo saldo: ${r.saldo_atual}.`);
        form.reset();
        await carregarProdutos();
      } catch (err) {
        mostrarToast(err.message);
        await carregarProdutos(op.value); // o saldo pode ter mudado em outra sessão
      }
    });
  }
  configurarEstoque(true);
  configurarEstoque(false);

  // ---------------------------------------------------------- Movimentações (histórico)
  const corpoMov = $("movements-table");
  if (corpoMov) {
    const filtroTipo = $("movement-type"), busca = $("movement-search");
    let movs = [];

    const desenhar = () => {
      const tipo = filtroTipo.value, termo = busca.value.toLowerCase().trim();
      const lista = movs.filter(m => (tipo === "TODOS" || m.tipo === tipo) &&
        `${m.produto} ${m.codigo} ${m.responsavel || ""}`.toLowerCase().includes(termo));
      corpoMov.innerHTML = lista.length ? lista.map(m => {
        const ent = m.tipo === "ENTRADA", dh = dataHora(m.data_hora);
        return `<tr>
          <td>${esc(m.codigo)}</td><td><b>${esc(m.produto)}</b></td>
          <td><i class="${ent ? "good" : "low"}">${ent ? "↙ Entrada" : "↗ Saída"}</i></td>
          <td class="${ent ? "pos" : "neg"}">${ent ? "+" : "−"}${m.quantidade}</td>
          <td>${dh.data}<span class="sub">${dh.hora}</span></td>
          <td>${esc(m.responsavel || "—")}</td><td>${esc(m.observacao || "—")}</td></tr>`;
      }).join("") : `<tr><td colspan="7" class="muted">Nenhuma movimentação encontrada.</td></tr>`;
      $("count-in").textContent = lista.filter(m => m.tipo === "ENTRADA").length;
      $("count-out").textContent = lista.filter(m => m.tipo === "SAIDA").length;
      $("movement-count").textContent = lista.length;
      $("movement-visible-count").textContent = `Mostrando ${lista.length} de ${movs.length} movimentações`;
    };
    api("/api/movimentacoes").then(d => { movs = d.movimentacoes; desenhar(); })
      .catch(err => mostrarToast(err.message));
    filtroTipo.addEventListener("change", desenhar);
    busca.addEventListener("input", desenhar);
  }
});
