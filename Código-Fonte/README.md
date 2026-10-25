# SonicStock — back-end e front-end integrados

Flask + MySQL (back-end) com páginas HTML/CSS/JS (front-end). Todas as telas agora leem e gravam no banco pela API.

## Como executar

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

1. No MySQL, execute `schema.sql` (cria o banco `bluestock` e as 5 tabelas) — **ou** confira se o seu banco atual tem as mesmas colunas (veja "Atenção" abaixo).
2. Crie o primeiro administrador: `python criar_usuario.py` (admin@sonicstock.com / 123456).
3. Suba o servidor: `python app.py` e abra http://127.0.0.1:5000

Credenciais do banco, se necessário, por variável de ambiente: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` e `SONICSTOCK_SECRET_KEY`.

## Atenção: nomes das colunas

O código original só revelava a tabela `usuario` (`id_usuario, nome, email, senha, perfil`). As demais colunas foram deduzidas do front-end — compare com o seu modelo (.mwb) e ajuste `schema.sql` ou os SQLs de `app.py`:

| Tabela | Colunas usadas |
|---|---|
| categoria | id_categoria, nome, descricao |
| fornecedor | id_fornecedor, nome, cnpj, telefone, email |
| produto | id_produto, codigo, nome, descricao, preco, quantidade, estoque_minimo, id_categoria, id_fornecedor |
| movimentacao_estoque | id_movimentacao, id_produto, id_usuario, tipo ('ENTRADA'/'SAIDA'), quantidade, data_hora, observacao |

## O que foi corrigido para back-end e front-end ficarem compatíveis

- `_layout.html` chamava `url_for('relatorio_estoque')` (rota inexistente) → quebrava todas as telas. Link removido (relatórios não têm tela nem RF ainda).
- Entrada, saída e histórico tinham `{{{{ ... }}}}` (chaves a mais) → corrigido.
- Back-end só tinha login e criação de usuário. Foram criadas as APIs usadas pelas telas (tabela abaixo).
- Páginas agora exigem login (redirecionam para `/`); `/usuarios` exige administrador. APIs respondem 401/403 em JSON.
- Front-end deixou de usar dados fictícios: tabelas, cartões, listas de produtos e formulários usam a API.
- Menu lateral: nome/perfil reais da sessão, botão **Sair** e link **Usuários** só para administrador.
- **Visual unificado:** Usuários, Entrada, Saída e Movimentações foram refeitas com o mesmo layout (`_layout.html`) e o mesmo `style.css` das demais telas (barra de busca, tabelas, selos de status, botões ✎/▤, formulário igual ao de produto). Os arquivos `telas_adicionais.css/js` foram removidos; a lógica foi para `app.js`.
- A coluna "Status" de usuários foi removida (não existe no banco).
- Removidos do pacote: `venv/`, `__pycache__/`, `templates.zip`, `static.zip` (cópias antigas) e o README antigo.

## API (JSON `{sucesso, mensagem, ...}`)

| Método e rota | Função |
|---|---|
| POST `/login`, POST `/logout`, GET `/api/me` | sessão |
| GET/POST `/api/categorias`, PUT/DELETE `/api/categorias/<id>` | categorias (com contagem de produtos) |
| GET/POST `/api/fornecedores`, PUT/DELETE `/api/fornecedores/<id>` | fornecedores |
| GET/POST `/api/produtos`, GET/PUT/DELETE `/api/produtos/<id>` | produtos (editar não altera o saldo) |
| POST `/api/movimentacoes/entrada`, `/saida` | atualiza saldo + grava histórico em **uma transação**; saída recusa saldo insuficiente |
| GET `/api/movimentacoes` | histórico (últimas 500) |
| GET `/api/dashboard` | totais e produtos com estoque baixo |
| GET/POST `/api/usuarios`, PUT/DELETE `/api/usuarios/<id>` | usuários (somente administrador); `POST /usuarios` original mantido |

## Decisões que você pode querer rever

- **Saída maior que o saldo é bloqueada** no servidor. Seu documento revisado removeu o RF019, mas o saldo negativo quebraria o histórico e a tela de saída já exige isso; remova o `if tipo == "SAIDA"...` em `registrar_movimentacao` se quiser o contrário.
- **Exclusão** de categoria/fornecedor/produto/usuário funciona sem regra extra, mas o banco impede excluir registros com vínculos (retorna 409 com mensagem). Não há regra condicional no código (RF007/011/015 foram removidos).
- **Permissões:** qualquer usuário logado opera produtos, categorias, fornecedores e estoque; somente administrador gerencia usuários (mesma regra do `POST /usuarios` original).
- Produto cadastrado com quantidade inicial > 0 gera uma entrada "Estoque inicial" no histórico.
- "Estoque baixo" = quantidade **menor ou igual** ao estoque mínimo.
